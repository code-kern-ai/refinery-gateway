from typing import Optional, Dict, Any

from service.search.search import generate_select_sql
from submodules.model.business_objects import attribute, data_slice, general, labeling_task, user_session


def export_records(project_id: str, export_options: Optional[Dict[str, Any]] = None):
    column_options =export_options.get("columns")
    row_options = export_options.get("rows")

    tasks = labeling_task.get_all(project_id)
    labeling_task_names = {str(lt.id): lt.name for lt in tasks if str(lt.id) in column_options.get("labeling_tasks")}

    attributes = attribute.get_all(project_id)
    attribute_names = {str(lt.id): lt.name for lt in attributes if str(lt.id) in column_options.get("attributes")}

    query = f"SELECT basic_record.id"

    attributes_select_query = __attributes_select_query(column_options.get("attributes"), attribute_names)
    if attributes_select_query:
        query += f", {attributes_select_query}"

    tasks_select_query = __labeling_tasks_select_query(column_options.get("labeling_tasks"), labeling_task_names)
    if tasks_select_query:
        query += f", {tasks_select_query}"

    record_data_query = __get_record_data_query(project_id, export_options.get("rows"))
    query += record_data_query

    labeling_task_data_query = build_column_query(project_id, column_options)
    query += labeling_task_data_query
    print(query)

    result_set = general.execute_all(query)
    print("result", len(result_set))

    #inner_row_query = build_row_query(project_id, export_options.get("rows"), attributes_query_select_part)
    #query = __get_base_id_query(project_id, inner_row_query, attributes_query_select_part)
    
    #tasks = labeling_task.get_all(project_id)
    #column_query = build_column_query(project_id, query, export_options.get("columns"))
    

def __attributes_select_query(selected_attribute_ids, attribute_names):
    attribute_json_selections = []
    for id in selected_attribute_ids:
        attribute_json_selections.append(f"basic_record.data::json->'{attribute_names.get(id)}' as {attribute_names.get(id)}")
    return ", ".join(attribute_json_selections)

def __labeling_tasks_select_query(selected_task_ids, task_names):
    task_selections = []
    for id in selected_task_ids:
        task_selections.append(f"{task_names.get(id)}.name as {task_names.get(id)}")
    return ", ".join(task_selections)


def __get_record_data_query(project_id: str, row_options: Dict[str, Any]):
    return __record_data_by_type(project_id, row_options)

def __record_data_by_type(project_id: str, row_options: Dict[str, Any]):
    if row_options.get("type") == "SLICE":
        return ___record_data_by_slice(project_id, row_options.get("id"))
    elif row_options.get("type") == "SESSION":
        return __record_data_by_session(project_id, row_options.get("id"))
    elif row_options.get("type") == "ALL":
        return __record_data_of_all(project_id)
    else:
        message = f"Type of filter {row_options.get('type')} for rows not allowed."
        raise Exception(message)


def ___record_data_by_slice(project_id, slice_id: str):
    slice = data_slice.get(project_id, slice_id)
    slice_type = slice.slice_type
    if slice_type == "STATIC_DEFAULT":
        return __record_data_by_static_slice_query(project_id, slice_id)
    elif slice_type == "DYNAMIC_DEFAULT":
        return __record_data_by_dynamic_slice(project_id, slice)
    else:
        message = f"Type of slice {slice_type} not allowed."
        raise Exception(message)

def __record_data_of_all(project_id: str):
    return f"""
    FROM (
        SELECT r.id, r.data
        FROM record r
        WHERE r.project_id = '{project_id}') basic_record"""

def __record_data_by_static_slice_query(project_id: str, slice_id: str):
    return f"""
    FROM (
        SELECT r.id, r.data
        FROM data_slice_record_association dsra
        JOIN record r
        ON r.id = dsra.record_id
        AND r.project_id = '{project_id}'
        AND dsra.project_id = '{project_id}'
        WHERE dsra.data_slice_id = '{slice_id}') basic_record"""

def __record_data_by_dynamic_slice(project_id, slice):
    dynamic_slice_select_query = generate_select_sql(project_id, slice.filter_data, 0, 0)
    return f"""
    FROM (
        SELECT r.id, r.data
        FROM record r
        JOIN (
           {dynamic_slice_select_query} 
        ) dsra
        ON r.id = dsra.record_id
        AND r.project_id = '{project_id}') basic_record"""

def __record_data_by_session(project_id, session_id: str):
    session = user_session.get(project_id, session_id)
    return f"""
    FROM (
        SELECT r.id, r.data
        FROM record r
        JOIN (
            {session.id_sql_statement}
        ) user_session
        ON r.id = user_session.record_id
        AND r.project_id = '{project_id}') basic_record"""


def build_column_query(project_id, column_options):
    labeling_task_ids = column_options.get("labeling_tasks")
    projects_tasks = labeling_task.get_all(project_id)
    labeling_task_names = {str(lt.id): lt.name for lt in projects_tasks if str(lt.id) in labeling_task_ids}
    header = [f"{labeling_task_names.get(id)}.{labeling_task_names.get(id)}" for id in labeling_task_ids]
    headers = ", ".join(header)

    query = ""
    for id in labeling_task_ids:
        query += build_labeling_task_column_query(project_id, id, labeling_task_names.get(id))
    print(20*"-")
    print(query)
    print(20*"-")
    return query


def build_labeling_task_column_query(project_id, labeling_task_id, name):
    return f"""
    LEFT JOIN (
        SELECT rla.record_id , ltl.name
    	FROM record_label_association rla 
    	INNER JOIN (
	        SELECT ltl.id, ltl.name
	        FROM labeling_task_label ltl
	        WHERE labeling_task_id = '{labeling_task_id}'
            AND ltl.project_id = '{project_id}'
	    ) ltl
   		ON rla.labeling_task_label_id  = ltl.id
        AND rla.project_id = '{project_id}'
   		WHERE rla.source_type = 'MANUAL'
    ) {name}
    ON {name}.record_id = basic_record.id"""


def build_top_select_query(column_options, tasks, attributes):
    labeling_task_ids = column_options.get("labeling_tasks")
    labeling_task_names = {str(lt.id): lt.name for lt in tasks if str(lt.id) in labeling_task_ids}
    task_fields = [f"{labeling_task_names.get(id)}.{labeling_task_names.get(id)}" for id in labeling_task_ids]

    attribute_ids =  column_options.get("attributes")
    attribute_names = {str(lt.id): lt.name for lt in attributes if str(lt.id) in column_options.get("attributes")}
    attribute_fields = [f"{attribute_names.get(id)}.{attribute_names.get(id)}" for id in attribute_ids]


    complete_fields = attribute_fields  # TODO insert here + task_fields
    field_concatination = ", ".join(complete_fields)
    return f"SELECT basic_record.id"