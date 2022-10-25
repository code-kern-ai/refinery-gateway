import random
import string
from typing import List, Optional, Dict, Any, Tuple, Union
from controller.transfer import export_parser

from service.search.search import generate_select_sql
from submodules.model.business_objects import (
    attribute,
    data_slice,
    general,
    labeling_task,
    user_session,
    information_source,
)
from submodules.model import enums
from submodules.model.models import LabelingTask
from util.miscellaneous_functions import first_item


def export_records(
    project_id: str, export_options: Optional[Dict[str, Any]] = None
) -> Any:

    column_options = export_options.get("columns")
    row_options = export_options.get("rows")

    attributes_options = column_options.get("attributes")
    task_options = column_options.get("labeling_tasks")
    sources_options = column_options.get("sources")
    with_user_id = column_options.get("with_user_id")

    tasks = labeling_task.get_all(project_id)
    labeling_task_names = {str(lt.id): lt.name for lt in tasks}
    labeling_tasks_by_id = {str(lt.id): lt for lt in tasks}

    attributes = attribute.get_all(project_id)
    attribute_names = {str(lt.id): lt.name for lt in attributes}

    if not attributes_options and not attributes_options and not sources_options:
        raise Exception("No export options found.")

    # prepare table names and build dictionaries for query creation
    (
        tables_meta_data,
        tables_mapping_classification,
    ) = __extract_table_meta_classification_data(
        project_id,
        task_options,
        labeling_tasks_by_id,
        attribute_names,
        labeling_task_names,
        sources_options,
        with_user_id,
    )

    # root select part
    select_part = f"SELECT basic_record.id::TEXT as record_id"
    if attributes_options:
        attributes_select_query = __attributes_select_query(
            attributes_options, attribute_names
        )
        select_part += f", {attributes_select_query}"

    if task_options and sources_options:
        tasks_select_query = __labeling_tasks_select_query(tables_meta_data)
        select_part += f", {tasks_select_query}"

    # row part and record data part
    record_data_query = __get_record_data_query(project_id, row_options)

    # task columns part
    classficiation_task_query = ""
    if task_options and sources_options:
        classficiation_task_query += __columns_by_table_meta_data_query(
            project_id, tables_meta_data
        )

    extraction_appends = get_extraction_task_appends(
        project_id, labeling_tasks_by_id, sources_options, True
    )

    # can be build dynamically
    final_query = f"""
    {extraction_appends["WITH"]}
    {select_part}
        {extraction_appends["SELECT"]}
    {record_data_query}
    {classficiation_task_query}
    {extraction_appends["FROM"]}
    WHERE basic_record.project_id = '{project_id}'
    """
    print("----- FINAL QUERY IS ------")
    final_query_cleaned = final_query.replace("\n\n", "\n")
    print(final_query_cleaned)

    mapping_dict = {**tables_mapping_classification, **extraction_appends["MAPPING"]}
    export_parser.parse(project_id, final_query_cleaned, mapping_dict)
    return general.execute_all(final_query_cleaned), tables_mapping_classification


def create_alias() -> str:
    return f"cd_{''.join(random.choice(string.ascii_lowercase) for _ in range(8))}"


def __extract_table_meta_classification_data(
    project_id: str,
    selected_tasks: List[str],
    tasks_by_id: Dict[str, LabelingTask],
    attribute_names: Dict[str, str],
    task_names: Dict[str, str],
    sources: Dict[str, Any],
    with_user_id: bool = False,
) -> Dict[str, Dict[str, Any]]:
    # Is used for combining table names according to convention and data for further creation of queries into a complex dict

    tables_mapping = {}
    tables_meta_data = {}
    for task_id in selected_tasks:
        task = tasks_by_id.get(task_id)

        if task.task_type == enums.LabelingTaskType.INFORMATION_EXTRACTION.value:
            continue

        attribute_name = attribute_names.get(str(task.attribute_id))
        attribute_and_task_name_part = (
            f"{attribute_name}__{task.name}" if attribute_name else f"__{task.name}"
        )

        for source in sources:
            full_table_name = ""
            addtional_confidence_table_name = ""
            tablename_dict = {}
            additional_confidence_table = {}

            if source.get("type") == enums.LabelSource.INFORMATION_SOURCE.value:
                source_entity = information_source.get(project_id, source.get("id"))
                if str(source_entity.labeling_task_id) == task_id:
                    full_table_name = (
                        f"{attribute_and_task_name_part}__{source_entity.name}"
                    )
                    tables_mapping[full_table_name] = create_alias()
                    tablename_dict["task_id"] = task_id
                    tablename_dict["task_type"] = task.task_type
                    tablename_dict["source_id"] = source.get("id")
                    tablename_dict["source_type"] = source.get("type")
                    tablename_dict["table_type"] = "task_data"
            else:
                full_table_name = (
                    f"{attribute_and_task_name_part}__{source.get('type')}"
                )
                tables_mapping[full_table_name] = create_alias()
                tablename_dict["source_type"] = source.get("type")
                tablename_dict["task_id"] = task_id
                tablename_dict["task_type"] = task.task_type
                tablename_dict["table_type"] = "task_data"

                if source.get("type") == enums.LabelSource.WEAK_SUPERVISION.value:
                    addtional_confidence_table_name = f"{full_table_name}_CONFIDENCE"
                    tables_mapping[addtional_confidence_table_name] = create_alias()
                    additional_confidence_table["original_table"] = tables_mapping.get(
                        full_table_name
                    )
                    additional_confidence_table["table_type"] = "confidence_data"
                    additional_confidence_table["source_type"] = source.get("type")
                    additional_confidence_table["task_id"] = task_id

            if tablename_dict and full_table_name:
                alias = tables_mapping.get(full_table_name)
                tables_meta_data[alias] = tablename_dict
                if additional_confidence_table:
                    tables_mapping[addtional_confidence_table_name] = create_alias()
                    tables_meta_data[
                        tables_mapping.get(addtional_confidence_table_name)
                    ] = additional_confidence_table
                if with_user_id:
                    additional_created_by_table = {}
                    additional_created_by_table["table_type"] = "user_data"
                    additional_created_by_table["original_table"] = tables_mapping.get(
                        full_table_name
                    )
                    addtional_created_by_name = full_table_name + "__created_by"
                    tables_mapping[addtional_created_by_name] = create_alias()
                    tables_meta_data[
                        tables_mapping.get(addtional_created_by_name)
                    ] = additional_created_by_table
    return tables_meta_data, tables_mapping


def __attributes_select_query(
    selected_attribute_ids: List[str], attribute_names: Dict[str, str]
) -> str:
    attribute_json_selections = []
    for id in selected_attribute_ids:
        attribute_json_selections.append(
            f"basic_record.data::json->'{attribute_names.get(id)}' as \"{attribute_names.get(id)}\""
        )
    return ",\n".join(attribute_json_selections)


def __labeling_tasks_select_query(tables_meta_data: Dict[str, Any]) -> str:
    task_selections = []
    for table_name, table_data in tables_meta_data.items():

        if table_data.get("table_type") == "confidence_data":
            task_selections.append(
                f"{table_data.get('original_table')}.confidence as {table_name}"
            )
        elif table_data.get("table_type") == "user_data":
            task_selections.append(
                f"{table_data.get('original_table')}.created_by as {table_name}"
            )
        elif table_data.get("task_type") == enums.LabelingTaskType.CLASSIFICATION.value:
            task_selections.append(f"{table_name}.name as {table_name}")
    return ",\n".join(task_selections)


def __get_record_data_query(project_id: str, row_options: Dict[str, Any]) -> str:
    return __record_data_by_type(project_id, row_options)


def __record_data_by_type(project_id: str, row_options: Dict[str, Any]) -> str:
    if row_options.get("type") == "SLICE":
        return ___record_data_by_slice(project_id, row_options.get("id"))
    elif row_options.get("type") == "SESSION":
        return __record_data_by_session(project_id, row_options.get("id"))
    elif row_options.get("type") == "ALL":
        return __record_data_without_reducing(project_id)
    else:
        message = (
            f"Type of filter {row_options.get('source_type')} for rows not allowed."
        )
        raise Exception(message)


def ___record_data_by_slice(project_id: str, slice_id: str) -> str:
    slice = data_slice.get(project_id, slice_id)
    slice_type = slice.slice_type
    if slice_type == enums.SliceTypes.STATIC_DEFAULT.value:
        return __record_data_by_static_slice_query(project_id, slice_id)
    elif slice_type == enums.SliceTypes.DYNAMIC_DEFAULT.value:
        return __record_data_by_dynamic_slice(project_id, slice)
    else:
        message = f"Type of slice {slice_type} not allowed."
        raise Exception(message)


def __record_data_by_static_slice_query(project_id: str, slice_id: str) -> str:
    return f"""
    FROM (
        SELECT r.id, r.data, r.project_id
        FROM data_slice_record_association dsra
        JOIN record r
        ON r.id = dsra.record_id
        AND r.project_id = '{project_id}'
        AND dsra.project_id = '{project_id}'
        WHERE dsra.data_slice_id = '{slice_id}') basic_record"""


def __record_data_by_dynamic_slice(project_id: str, slice: str) -> str:
    dynamic_slice_select_query = generate_select_sql(
        project_id, slice.filter_data, 0, 0
    )
    return f"""
    FROM (
        SELECT r.id, r.data, r.project_id
        FROM (
           {dynamic_slice_select_query} 
        ) dsra
        INNER JOIN record r
        ON r.id = dsra.record_id
        AND r.project_id = '{project_id}') basic_record"""


def __record_data_by_session(project_id: str, session_id: str) -> str:
    session = user_session.get(project_id, session_id)
    return f"""
    FROM (
        SELECT r.id, r.data, r.project_id
        FROM (
            {session.id_sql_statement}
        ) user_session
        INNER JOIN record r
        ON r.id = user_session.record_id
        AND r.project_id = '{project_id}') basic_record"""


def __record_data_without_reducing(project_id: str) -> str:
    return f"""
    FROM (
        SELECT r.id, r.data, r.project_id
        FROM record r
        WHERE r.project_id = '{project_id}') basic_record"""


def __columns_by_table_meta_data_query(
    project_id: str, tables_meta_data: Dict[str, Any]
) -> str:
    query = ""
    for table_name in tables_meta_data:
        table_meta_data = tables_meta_data.get(table_name)
        if not table_meta_data.get("table_type") == "task_data":
            continue

        if (
            table_meta_data.get("task_type")
            == enums.LabelingTaskType.CLASSIFICATION.value
        ):
            query += __classification_column_by_table_meta_data_query(
                project_id,
                table_meta_data.get("task_id"),
                table_name,
                table_meta_data.get("source_id"),
                table_meta_data.get("source_type"),
            )
        else:
            message = f"Task type {table_meta_data.get('task_type')} not allowed."
            raise Exception(message)
    return query


def __classification_column_by_table_meta_data_query(
    project_id: str,
    labeling_task_id: str,
    table_name: str,
    source_id: str,
    source_type: str,
) -> str:
    return f"""
    LEFT JOIN (
        SELECT rla.record_id, {table_name}_ltl_outer.name, rla.confidence, rla.created_by
    	FROM record_label_association rla 
    	INNER JOIN (
	        SELECT {table_name}_ltl_inner.id, {table_name}_ltl_inner.name
	        FROM labeling_task_label {table_name}_ltl_inner
	        WHERE labeling_task_id = '{labeling_task_id}'
            AND {table_name}_ltl_inner.project_id = '{project_id}'
	    ) {table_name}_ltl_outer
   		ON rla.labeling_task_label_id  = {table_name}_ltl_outer.id
        AND rla.project_id = '{project_id}'
   		WHERE {__source_constraint(source_id, source_type)}
        AND rla.return_type = '{enums.InformationSourceReturnType.RETURN.value}'
    ) {table_name}
    ON {table_name}.record_id = basic_record.id"""


def __source_constraint(source_id: str, source_type: str) -> str:  # TODO enums here
    if source_type == enums.LabelSource.MANUAL.value:
        return __manual_source_filtering()
    elif source_type == enums.LabelSource.INFORMATION_SOURCE.value:
        return __information_source_source_filtering(source_id)
    elif source_type == enums.LabelSource.MODEL_CALLBACK.value:
        return __model_source_filtering()
    elif source_type == enums.LabelSource.WEAK_SUPERVISION.value:
        return __weak_supervision_source_filtering()
    else:
        message = f"Type {source_type} not allowed for label sources."
        raise Exception(message)


def __manual_source_filtering() -> str:
    return f"""rla.source_type = '{enums.LabelSource.MANUAL.value}'
    AND rla.is_valid_manual_label"""


def __information_source_source_filtering(source_id: str) -> str:
    return f"""rla.source_type = '{enums.LabelSource.INFORMATION_SOURCE.value}'
                AND rla.source_id = '{source_id}'"""


def __model_source_filtering() -> str:
    return f"rla.source_type = '{enums.LabelSource.MODEL_CALLBACK.value}'"


def __weak_supervision_source_filtering() -> str:
    return f"rla.source_type = '{enums.LabelSource.WEAK_SUPERVISION.value}'"


def get_extraction_task_appends(
    project_id: str,
    labeling_tasks_by_id: Dict[str, LabelingTask],
    label_sources: List[Dict[str, str]],
    with_user_id: bool = False,
) -> Dict[str, Union[str, Dict[str, str]]]:
    return_values = {
        "WITH": "",
        "SELECT": "",
        "FROM": "",
        "EX_QUERIES": None,
        "MAPPING": {},
    }
    if len(labeling_tasks_by_id) == 0:
        return return_values

    has_extraction = False
    counter = 1
    extraction_queries = {}
    for key in labeling_tasks_by_id:
        if (
            labeling_tasks_by_id[key].task_type
            != enums.LabelingTaskType.INFORMATION_EXTRACTION.value
        ):
            continue
        for source in label_sources:
            ed_part = __get_extraction_data_query_and_select(
                project_id,
                counter,
                labeling_tasks_by_id[key],
                source,
            )
            extraction_queries |= ed_part
            x = first_item(ed_part)
            return_values["SELECT"] += x["SELECT"]
            return_values["FROM"] += x["FROM"]
            return_values["MAPPING"] |= x["MAPPING"]
            counter += 1

        has_extraction = True

    if has_extraction:
        return_values["WITH"] = __get_with_query_extraction_tasks(
            project_id, with_user_id
        )
        return_values["EX_QUERIES"] = extraction_queries
    return return_values


def __get_extraction_data_query_and_select(
    project_id, query_counter: int, task: LabelingTask, source: Dict[str, str]
) -> Dict[str, Tuple[str, str]]:
    source_type = source["type"]
    try:
        source_type_parsed = enums.LabelSource[source_type.upper()]
    except KeyError:
        raise ValueError(f"Invalid comment category: {source_type}")

    on_add = f"AND ed.source_type = '{source_type}'"
    if source_type_parsed == enums.LabelSource.MANUAL:
        on_add += f" AND ed.is_valid_manual_label = TRUE "
    elif source_type_parsed == enums.LabelSource.INFORMATION_SOURCE:
        on_add += f" AND ed.source_id = '{source['source_id']}' "
    else:
        # WEAK_SUPERVISION & MODEL_CALLBACK -> nothing to do
        pass
    query_alias = "ed" + str(query_counter)

    query = f"""LEFT JOIN (
        SELECT ed.record_id, ed.project_id,ed.task_data,ti.token_info
        FROM extraction_data ed
        INNER JOIN token_info ti
            ON ed.record_id = ti.record_id AND ed.project_id = ti.project_id AND ti.attribute_id = ed.attribute_id
            AND ed.task_id = '{str(task.id)}' {on_add}
    ) {query_alias}
        ON {query_alias}.record_id = basic_record.id AND {query_alias}.project_id = '{project_id}'
    """
    attribute_name = __get_attribute_name_from_task(task)
    base_name = f"{attribute_name}__{task.name}__{source_type}"
    if source_type_parsed == enums.LabelSource.INFORMATION_SOURCE:
        base_name += f"__{source['name']}"

    td_mapping = f"{query_alias}_td"
    ti_mapping = f"{query_alias}_ti"
    mapping = {
        td_mapping: f"{base_name}__task_data",
        ti_mapping: f"{base_name}__token_info",
    }

    select = f""",\n    {query_alias}.task_data \"{td_mapping}\",\n    {query_alias}.token_info \"{ti_mapping}\""""

    return {
        query_alias: {
            "SELECT": select,
            "FROM": query,
            "MAPPING": mapping,
            "base_name": base_name,
            "task": task,
        }
    }


def __get_attribute_name_from_task(task: LabelingTask) -> str:
    return attribute.get(task.project_id, task.attribute_id).name


def __get_with_query_extraction_tasks(
    project_id: str, with_user_id: bool = False
) -> str:
    created_by_add = ""
    if with_user_id:
        created_by_add = ",\n   	         'created_by', rla.created_by"
    return f"""WITH token_info AS (
	SELECT 
		record_id, 
		project_id,
		attribute_id,
		jsonb_build_object(
			'token_count',num_token,
			'char_count',num_char) token_info
	FROM(
		SELECT r.id record_id, r.project_id, a.id attribute_id, rats.num_token, LENGTH(r.data->>a.name) num_char
		FROM attribute a
		INNER JOIN record r
		    ON a.project_id = r.project_id
		INNER JOIN record_attribute_token_statistics rats
		    ON a.project_id = rats.project_id AND a.id = rats.attribute_id AND r.id = rats.record_id
		WHERE a.data_type = '{enums.DataTypes.TEXT.value}'
		AND a.project_id = '{project_id}'
	) i
),
extraction_data AS (
	 SELECT
	     record_id,
	     project_id,
	     source_type,
	     is_valid_manual_label,
	     source_id,
	     task_id,
	     attribute_id,	     
	     array_agg(
	         jsonb_build_object(
	         'rla_id',rla_id,
	         'rla_data',rla_data)) task_data
	 FROM (
	     SELECT
	         rla.record_id,
	         rla.project_id,
	         rla.source_type,
	         rla.is_valid_manual_label,
	         rla.source_id,
	         lt.id task_id,
	         lt.attribute_id,
	         rla.id rla_id,
	         jsonb_build_object(
		         'confidence', CASE WHEN source_type='{enums.LabelSource.MANUAL.value}' THEN NULL ELSE ROUND(rla.confidence::numeric,4) END,
		         'source_type', rla.source_type,
		         'token', token.token,
		         'label_name', ltl.name{created_by_add})rla_data
	     FROM record_label_association rla
	     INNER JOIN (
	         SELECT rlat.project_id, rlat.record_label_association_id rla_id, array_agg(rlat.token_index ORDER BY token_index) token
	         FROM record_label_association_token rlat
	         GROUP BY rlat.project_id, rlat.record_label_association_id
	     ) token
	     	ON rla.project_id = token.project_id AND rla.id = token.rla_id
	     INNER JOIN labeling_task_label ltl
	     	ON rla.project_id = ltl.project_id AND rla.labeling_task_label_id = ltl.id
	     INNER JOIN labeling_task lt
	     	ON ltl.project_id = lt.project_id AND lt.id = ltl.labeling_task_id	     
	     WHERE rla.return_type = '{enums.InformationSourceReturnType.YIELD.value}' --ensure extraction
	     AND rla.project_id ='{project_id}'
	 ) extract_data_grabber
	 GROUP BY record_id, project_id,source_type,is_valid_manual_label,source_id,task_id,attribute_id
)
    """
