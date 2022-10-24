from typing import List, Optional, Dict, Any

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


def export_records(
    project_id: str, export_options: Optional[Dict[str, Any]] = None
) -> Any:  # returns complex record and rla combination
    # collecting data for database query creation
    column_options = export_options.get("columns")
    row_options = export_options.get("rows")

    attributes_options = column_options.get("attributes")
    task_options = column_options.get("labeling_tasks")
    sources_options = column_options.get("sources")

    tasks = labeling_task.get_all(project_id)
    labeling_task_names = {str(lt.id): lt.name for lt in tasks}
    labeling_tasks_by_id = {str(lt.id): lt for lt in tasks}

    attributes = attribute.get_all(project_id)
    attribute_names = {str(lt.id): lt.name for lt in attributes}

    if not attributes_options and not attributes_options and not sources_options:
        raise Exception("No export options found.")

    # prepare table names and build dictionaries for query creation
    tables_meta_data = __extract_table_meta_data(
        project_id,
        task_options,
        labeling_tasks_by_id,
        attribute_names,
        labeling_task_names,
        sources_options,
    )

    # root select part
    query = f"SELECT basic_record.id"
    if attributes_options:
        attributes_select_query = __attributes_select_query(
            attributes_options, attribute_names
        )
        query += f", {attributes_select_query}"

    if task_options and sources_options:
        tasks_select_query = __labeling_tasks_select_query(tables_meta_data)
        query += f", {tasks_select_query}"

    # row part and record data part
    record_data_query = __get_record_data_query(project_id, row_options)
    query += record_data_query

    # task columns part
    if task_options and sources_options:
        labeling_task_data_query = __columns_by_table_meta_data_query(
            project_id, tables_meta_data
        )
        query += labeling_task_data_query

    print(query)
    return general.execute_all(query)


def __extract_table_meta_data(
    project_id: str,
    selected_tasks: List[str],
    tasks_by_id: Dict[str, LabelingTask],
    attribute_names: Dict[str, str],
    task_names: Dict[str, str],
    sources: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    # Is used for combining table names according to convention and data for further creation of queries into a complex dict

    tables_meta_data = {}
    for task_id in selected_tasks:
        task = tasks_by_id.get(task_id)
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
                    tablename_dict["task_id"] = task_id
                    tablename_dict["task_type"] = task.task_type
                    tablename_dict["source_id"] = source.get("id")
                    tablename_dict["source_type"] = source.get("type")
                    tablename_dict["confidence_table"] = False
            else:
                full_table_name = (
                    f"{attribute_and_task_name_part}__{source.get('type')}"
                )
                tablename_dict["source_type"] = source.get("type")
                tablename_dict["task_id"] = task_id
                tablename_dict["task_type"] = task.task_type
                tablename_dict["confidence_table"] = False

                if (
                    source.get("type") == enums.LabelSource.WEAK_SUPERVISION.value
                    and task.task_type == enums.LabelingTaskType.CLASSIFICATION.value
                ):
                    addtional_confidence_table_name = f"{full_table_name}_CONFIDENCE"
                    additional_confidence_table["original_table"] = full_table_name
                    additional_confidence_table["confidence_table"] = True
                    additional_confidence_table["source_type"] = source.get("type")
                    additional_confidence_table["task_id"] = task_id

            if tablename_dict and full_table_name:
                tables_meta_data[full_table_name] = tablename_dict
                if additional_confidence_table:
                    tables_meta_data[
                        addtional_confidence_table_name
                    ] = additional_confidence_table

    return tables_meta_data


def __attributes_select_query(
    selected_attribute_ids: List[str], attribute_names: Dict[str, str]
) -> str:
    attribute_json_selections = []
    for id in selected_attribute_ids:
        attribute_json_selections.append(
            f"basic_record.data::json->'{attribute_names.get(id)}' as {attribute_names.get(id)}"
        )
    return ",\n".join(attribute_json_selections)


def __labeling_tasks_select_query(tables_meta_data: Dict[str, Any]) -> str:
    task_selections = []
    for table_name, table_data in tables_meta_data.items():

        if table_data.get("confidence_table"):
            task_selections.append(
                f"{table_data.get('original_table')}.confidence as {table_name}"
            )
        elif (
            table_data.get("task_type")
            == enums.LabelingTaskType.INFORMATION_EXTRACTION.value
        ):
            task_selections.append(f"{table_name}.extraction_data as {table_name}")
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
        SELECT r.id, r.data
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
        SELECT r.id, r.data
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
        SELECT r.id, r.data
        FROM (
            {session.id_sql_statement}
        ) user_session
        INNER JOIN record r
        ON r.id = user_session.record_id
        AND r.project_id = '{project_id}') basic_record"""


def __record_data_without_reducing(project_id: str) -> str:
    return f"""
    FROM (
        SELECT r.id, r.data
        FROM record r
        WHERE r.project_id = '{project_id}') basic_record"""


def __columns_by_table_meta_data_query(
    project_id: str, tables_meta_data: Dict[str, Any]
) -> str:
    query = ""
    for table_name in tables_meta_data:
        table_meta_data = tables_meta_data.get(table_name)
        if table_meta_data.get("confidence_table"):
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
        elif (
            table_meta_data.get("task_type")
            == enums.LabelingTaskType.INFORMATION_EXTRACTION.value
        ):
            query += __extraction_column_by_table_meta_data_query(
                project_id,
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
        SELECT rla.record_id, {table_name}_ltl_outer.name, rla.confidence
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


def __extraction_column_by_table_meta_data_query(
    project_id: str, table_name: str, source_id: str, source_type: str
) -> str:
    return f"""
    LEFT JOIN(
        SELECT 
            extract_data_grabber.record_id,
            extract_data_grabber.project_id,
            array_agg(
                json_build_object(
                'rla_id',extract_data_grabber.rla_id,
                'rla_data',extract_data_grabber.rla_data)) extraction_data
        FROM (
            SELECT
                rla.record_id,
                rla.project_id,
                rla.id rla_id,
                json_build_object(
                'confidence', ROUND(rla.confidence::numeric,4),
                'source_type', rla.source_type,
                'token', token.token,
                'label_name', ltl.name,
                'token_count',token_info.num_token,
                'char_count',token_info.num_char
                    )rla_data
            FROM record_label_association rla
            INNER JOIN (
                SELECT rlat.project_id, rlat.record_label_association_id rla_id, array_agg(rlat.token_index ORDER BY token_index) token
                FROM record_label_association_token rlat
                WHERE rlat.project_id = '{project_id}'
                GROUP BY rlat.project_id, rlat.record_label_association_id
            ) token
            ON rla.project_id = token.project_id AND rla.id = token.rla_id
            INNER JOIN labeling_task_label ltl
            ON rla.project_id = ltl.project_id AND rla.labeling_task_label_id = ltl.id
            INNER JOIN labeling_task lt
            ON ltl.project_id = lt.project_id AND lt.id = ltl.labeling_task_id
            INNER JOIN (
                SELECT r.id record_id, r.project_id, a.id attribute_id, rats.num_token, LENGTH(r.data->>a.name) num_char
                FROM attribute a
                INNER JOIN record r
                    ON a.project_id = r.project_id
                INNER JOIN record_attribute_token_statistics rats
                    ON a.project_id = rats.project_id AND a.id = rats.attribute_id AND r.id = rats.record_id
                WHERE a.project_id = '{project_id}' 
            ) token_info
                ON rla.record_id = token_info.record_id AND lt.attribute_id = token_info.attribute_id AND rla.project_id = token_info.project_id
            WHERE rla.return_type = '{enums.InformationSourceReturnType.YIELD.value}' --ensure extraction
            AND rla.project_id ='{project_id}'
            AND  {__source_constraint(source_id, source_type)}
        ) extract_data_grabber
        GROUP BY extract_data_grabber.record_id, extract_data_grabber.project_id
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
