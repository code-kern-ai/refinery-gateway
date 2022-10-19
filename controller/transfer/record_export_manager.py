from typing import Optional, Dict, Any

from service.search.search import generate_select_sql
from submodules.model.business_objects import data_slice, user_session


def export_records(project_id: str, export_options: Optional[Dict[str, Any]] = None):
    query = build_row_query(project_id, row_options=export_options.get("rows"))
    print(query)


def build_row_query(project_id: str, row_options: Dict[str, Any]):
    join_query = __build_rows_by_type(project_id, row_options)
    query = __get_base_query(project_id, join_query)
    return query


def __build_rows_by_type(project_id: str, row_options: Dict[str, Any]):
    if row_options.get("type") == "SLICE":
        return __build_rows_by_slice(project_id, row_options.get("id"))
    elif row_options.get("type") == "SESSION":
        return __build_rows_by_session(project_id, row_options.get("id"))
    elif row_options.get("type") == "ALL":
        return ""
    else:
        message = f"Type of filter {row_options.get('type')} for rows not allowed."
        raise Exception(message)


def __build_rows_by_slice(project_id, slice_id: str):
    slice = data_slice.get(project_id, slice_id)
    slice_type = slice.slice_type
    if slice_type == "STATIC":
        return __build_rows_by_static_slice(slice_id)
    elif slice_type == "DYNAMIC_DEFAULT":
        return __build_rows_by_dynamic_slice(project_id, slice)
    else:
        message = f"Type of slice {slice_type} not allowed."
        raise Exception(message)

def __build_rows_by_static_slice(slice_id: str):
    return f"""INNER JOIN (SELECT dsra.record_id
    FROM data_slice_record_association dsra
    WHERE dsra.data_slice_id = '{slice_id}') dsra
    ON r.id = dsra.record_id"""

def __build_rows_by_dynamic_slice(project_id, slice):
    dynamic_slice_select_query = generate_select_sql(project_id, slice.filter_data, 0, 0)
    return f"""INNER JOIN ({dynamic_slice_select_query}) dsra
    ON r.id = dsra.record_id"""

def __build_rows_by_session(project_id, session_id: str):
    session = user_session.get(project_id, session_id)
    return f"""INNER JOIN ({session.id_sql_statement}) session
    ON r.id = session.record_id"""

def __get_base_query(project_id: str, join_query: str):
    query = f"""
    SELECT r.id
    FROM record r"""
    if join_query:
        query += f"""
        {join_query}"""

    query += f"""
    WHERE r.project_id = '{project_id}'"""  
    return query