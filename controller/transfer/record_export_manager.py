from typing import Optional, Dict, Any

from service.search.search import generate_select_sql
from submodules.model.business_objects import attribute, data_slice, general, labeling_task, user_session, information_source


def export_records(project_id: str, export_options: Optional[Dict[str, Any]] = None):
    column_options =export_options.get("columns")
    row_options = export_options.get("rows")

    tasks = labeling_task.get_all(project_id)
    labeling_task_names = {str(lt.id): lt.name for lt in tasks if str(lt.id) in column_options.get("labeling_tasks")}
    labeling_tasks_by_id = {str(lt.id): lt for lt in tasks}

    attributes = attribute.get_all(project_id)
    attribute_names = {str(lt.id): lt.name for lt in attributes if str(lt.id) in column_options.get("attributes")}

    tables_meta_data = __extract_table_meta_data(project_id, column_options.get("labeling_tasks"), labeling_tasks_by_id, attribute_names, labeling_task_names, column_options.get("sources"))
    query = f"SELECT basic_record.id"

    attributes_select_query = __attributes_select_query(column_options.get("attributes"), attribute_names)
    if attributes_select_query:
        query += f", {attributes_select_query}"

    tasks_select_query = __labeling_tasks_select_query(tables_meta_data.keys())
    if tasks_select_query:
        query += f", {tasks_select_query}"

    record_data_query = __get_record_data_query(project_id, row_options)
    query += record_data_query

    labeling_task_data_query = build_columns_by_table_meta_data(project_id, tables_meta_data)
    query += labeling_task_data_query
    print(tables_meta_data)
    print(query)
    result_set = general.execute_all(query)
    print(len(result_set))

def __extract_table_meta_data(project_id, selected_tasks, tasks_by_id, attribute_names, task_names, sources):
    tables_meta_data = {}
    for task_id in selected_tasks:
        task = tasks_by_id.get(task_id)
        attribute_task_name = ""
        if task.attribute_id:
            attribute_task_name = attribute_names.get(str(task.attribute_id))

        attribute_task_name += f"__{task_names.get(task_id)}"

        for source in sources:
            full_table_name = ""
            tablename_dict = {}
            if source.get("type") == "INFORMATION_SOURCE": # TODO add enum here
                source_entity = information_source.get(project_id, source.get("id"))
                print(source_entity.name)

                if str(source_entity.labeling_task_id) == task_id:
                    full_table_name = f"{attribute_task_name}__{source_entity.name}"
                    tablename_dict["type"] = source.get("type") 
                    tablename_dict["task_id"] = task_id
                    tablename_dict["source_id"] = source.get("id") 
            else:
                full_table_name = f"{attribute_task_name}__{source.get('type')}"
                tablename_dict["type"] = source.get("type") 
                tablename_dict["task_id"] = task_id

            if tablename_dict and full_table_name:
                tables_meta_data[full_table_name] = tablename_dict
    return tables_meta_data

def __attributes_select_query(selected_attribute_ids, attribute_names):
    attribute_json_selections = []
    for id in selected_attribute_ids:
        attribute_json_selections.append(f"basic_record.data::json->'{attribute_names.get(id)}' as {attribute_names.get(id)}")
    return ", ".join(attribute_json_selections)

def __labeling_tasks_select_query(tablenames):
    task_selections = []
    for tablename in tablenames:
        task_selections.append(f"{tablename}.name as {tablename}")
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

def build_columns_by_table_meta_data(project_id, tables_meta_data):
    query = ""
    for table_name in tables_meta_data:
            table_meta_data = tables_meta_data.get(table_name)
            query += build_labeling_task_column_query(project_id, table_meta_data.get("task_id"), table_name, table_meta_data.get("type"), table_meta_data.get("source_id"))
    return query


def build_labeling_task_column_query(project_id, labeling_task_id, table_name, type, source_id):
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
   		{__source_constraint(type, source_id)}
    ) {table_name}
    ON {table_name}.record_id = basic_record.id"""


def __source_constraint(type, source_id): #TODO enums here
        if type == "MANUAL":
            return __manual_source()
        elif type == "INFORMATION_SOURCE":
            return __information_source_source(source_id)
        elif type == "MODEL_CALLBACK":
            return __model_source()
        elif type == "WEAK_SUPERVISION":
            return __weak_supervision_source()
        else:
            message = f"Type {type} not allowed for label sources."
            raise Exception(message)



def __manual_source():
    return "WHERE rla.source_type = 'MANUAL'"

def __weak_supervision_source():
    return "WHERE rla.source_type = 'WEAK_SUPERVISION'"

def __model_source():
    return "WHERE rla.source_type = 'MODEL_CALLBACK'"

def __information_source_source(source_id):
    return f"""WHERE rla.source_type = 'INFORMATION_SOURCE'
                AND rla.source_id = '{source_id}'"""