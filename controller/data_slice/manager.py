from typing import Dict, Any, List, Optional

from submodules.model import DataSlice
from submodules.model import enums
from submodules.model.business_objects import general, data_slice, embedding
import uuid
from service.search import search
from controller.data_slice import neural_search_connector
from submodules.model.enums import SliceTypes


def get_all_data_slices(
    project_id: str, slice_type: Optional[str] = None
) -> List[DataSlice]:
    parsed = None
    if slice_type:
        try:
            parsed = enums.SliceTypes[slice_type.upper()]
        except KeyError:
            raise ValueError(f"Invalid SliceTypes: {slice_type}")
    return data_slice.get_all(project_id, parsed)


def count_items(project_id: str, data_slice_id: str) -> int:
    data_slice_item: DataSlice = data_slice.get(project_id, data_slice_id)
    if not data_slice_item:
        raise ValueError(f"unkown slice id {data_slice_id}")
    if not data_slice_item.static:
        raise ValueError(f"Slice {data_slice_id} - {data_slice_item.name} isn't static")
    return general.execute_distinct_count(data_slice_item.count_sql)


def __create_data_slice_record_associations(
    project_id: str, data_slice_id: str, filter_data: List[Dict[str, Any]]
) -> None:
    count_sql: str = search.generate_count_sql(project_id, filter_data)
    count: int = general.execute_distinct_count(count_sql)

    if count > 10000:
        raise Exception("Too many records for static slice.")

    data_slice.delete_associations(project_id, data_slice_id, with_commit=True)
    insert_statement: str = (
        search.generate_data_slice_record_associations_insert_statement(
            project_id, filter_data, data_slice_id
        )
    )
    general.execute(insert_statement)
    data_slice.update_data_slice(
        project_id,
        data_slice_id,
        filter_data=filter_data,
        count=count,
        count_sql=count_sql,
        with_commit=True,
    )


def create_data_slice(
    project_id: str,
    user_id: str,
    name: str,
    filter_raw: Dict[str, Any],
    filter_data: List[Dict[str, Any]],
    static: bool,
    slice_type: Optional[str] = None,
    info: Optional[Dict[str, Any]] = None,
) -> DataSlice:

    if slice_type is None:
        if static:
            slice_type = SliceTypes.STATIC_DEFAULT.value
        else:
            slice_type = SliceTypes.DYNAMIC_DEFAULT.value

    data_slice_item: DataSlice = data_slice.create(
        project_id=project_id,
        created_by=user_id,
        name=name,
        filter_raw=filter_raw,
        static=static,
        slice_type=slice_type,
        info=info,
        with_commit=True,
    )
    if static:
        __create_data_slice_record_associations(
            project_id, data_slice_item.id, filter_data
        )
    return data_slice_item


def update_data_slice(
    project_id: str,
    data_slice_id: str,
    filter_data: List[Dict[str, Any]],
    filter_raw: Dict[str, Any],
    static: bool,
) -> None:
    if static:
        __create_data_slice_record_associations(project_id, data_slice_id, filter_data)

    data_slice.update_data_slice(
        project_id,
        data_slice_id,
        static=static,
        filter_raw=filter_raw,
        filter_data=filter_data,
        with_commit=True,
    )


def delete_data_slice(project_id: str, data_slice_id: str) -> None:
    data_slice.delete(project_id, data_slice_id, with_commit=True)


def create_outlier_slice(project_id: str, user_id: str, embedding_id: str) -> DataSlice:
    outlier_ids, outlier_scores = neural_search_connector.request_outlier_detection(
        project_id, embedding_id, 100
    )
    filter_data = [
        {
            "RELATION": "NONE",
            "NEGATION": False,
            "TARGET_TABLE": "RECORD",
            "TARGET_COLUMN": "ID",
            "OPERATOR": "IN",
            "VALUES": outlier_ids,
        }
    ]

    embedding_name = embedding.get(project_id, embedding_id).name
    info = {
        "embedding": embedding_name,
    }
    data_slice_item = create_data_slice(
        project_id=project_id,
        user_id=user_id,
        name=str(uuid.uuid4()),
        filter_raw=None,
        filter_data=filter_data,
        static=True,
        slice_type=SliceTypes.STATIC_OUTLIER.value,
        info=info,
    )
    data_slice.update_data_slice_record_association_outlier_scores(
        project_id, data_slice_item.id, outlier_ids, outlier_scores, with_commit=True
    )
    return data_slice_item


def update_slice_type_manual_for_all() -> None:
    data_slice.update_slice_type_manual_for_all(with_commit=True)
