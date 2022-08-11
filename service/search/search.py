from dataclasses import dataclass
import zlib
from typing import Tuple, Dict, List, Any, Optional

from exceptions.exceptions import TooManyRecordsForStaticSliceException
from graphql_api import types
from graphql_api.types import ExtendedSearch
from submodules.model import UserSessions
from util.notification import create_notification
from submodules.model.enums import (
    NotificationType,
    SliceTypes,
    Tablenames,
    RecordCategory,
)
from .search_enum import (
    FilterDataDictKeys,
    SearchQueryTemplate,
)
from .search_helper import (
    build_order_by_column,
    build_order_by_record_data,
    build_order_column_record_data,
    build_query_template,
    build_order_by_table_select,
    get_query_template,
    build_search_condition,
)


from submodules.model.business_objects import (
    attribute,
    data_slice,
    general,
    user_session,
)


@dataclass
class UserSessionData:
    project_id: str
    id_sql_statement: str
    count_sql_statement: str
    last_count: int
    created_by: str
    random_seed: float


__seed_number = None


def generate_data_slice_record_associations_insert_statement(
    project_id: str, filter_parsed: List[Dict[str, Any]], data_slice_id: str
) -> str:
    sql_select = generate_select_sql(project_id, filter_parsed, 0, 0, True)
    sql_with_slice_column = __add_data_slice_id_and_project_id_column(
        sql_select, data_slice_id, project_id
    )
    sql_insert_statement = __add_insert_into_dsra_statement(sql_with_slice_column)
    return sql_insert_statement


def resolve_records_by_static_slice(
    user_id: str,
    project_id: str,
    slice_id: str,
    order_by: Dict[str, str],
    limit: int,
    offset: int,
) -> ExtendedSearch:
    global __seed_number
    local_seed = None
    order_by_add = None
    select_add = None
    from_add = None

    slice = data_slice.get(project_id, slice_id, True)
    if not slice:
        raise ValueError(f"Can't find slice with id {slice_id} in project.")

    if slice.slice_type == SliceTypes.STATIC_OUTLIER.value:
        order_by_add = "ORDER BY outlier_score DESC"
        select_add = ", outlier_score"
    else:
        if order_by:
            order_by_add = __build_order_by(order_by, project_id)
            select_add, from_add = __build_order_by_subquery(order_by, project_id)

    sql = __basic_query(
        project_id,
        limit,
        offset,
        slice_id,
        order_by_add,
        select_add,
        from_add,
    )
    count_sql = __count_dsra(slice_id)
    count = general.execute_first(count_sql)[0]

    extended_search = ExtendedSearch(
        sql=sql,
        query_limit=limit,
        query_offset=offset,
        full_count=count,
    )
    if __seed_number:
        local_seed = __seed_number
        __seed_number = None
        general.execute(f"SELECT setseed({local_seed});")

    extended_search.record_list = [record for record in general.execute_all(sql)]

    select_statement = __select_record_data(
        project_id, slice_id, order_by_add, select_add, from_add
    )
    id_sql_statement = __build_final_query(select_statement, project_id, False, True)
    user_session_data = __create_static_user_session_object(
        project_id,
        user_id,
        id_sql_statement,
        count_sql,
        count,
        local_seed,
    )
    extended_search.session_id = __write_user_session_entry(user_session_data)
    return extended_search


def resolve_extended_search(
    project_id: str,
    user_id: str,
    filter_data: List[Dict[str, Any]],
    limit: int,
    offset: int,
) -> ExtendedSearch:
    global __seed_number
    local_seed = None

    __ensure_text(filter_data)
    sql_statement_count = generate_count_sql(project_id, filter_data)

    count = general.execute_distinct_count(sql_statement_count)

    sql_statement_normal = generate_select_sql(project_id, filter_data, limit, offset)

    extended_search = ExtendedSearch(
        sql=sql_statement_normal,
        query_limit=limit,
        query_offset=offset,
        full_count=count,
    )
    if __seed_number:
        local_seed = __seed_number
        __seed_number = None
        general.execute(f"SELECT setseed({local_seed});")
    extended_search.record_list = [
        record for record in general.execute_all(sql_statement_normal)
    ]

    user_session_data = __create_default_user_session_object(
        project_id, user_id, filter_data, sql_statement_count, count, local_seed
    )

    extended_search.session_id = __write_user_session_entry(user_session_data)
    return extended_search


def __ensure_text(filter_data: List[Dict[str, Any]]) -> None:
    for idx, element in enumerate(filter_data):
        if isinstance(element, str):
            filter_data[idx] = element.replace("'", "''")
            continue
        if isinstance(element, dict):
            for key in element:
                if isinstance(element[key], str):
                    element[key] = element[key].replace("'", "''")
                    continue
                if isinstance(element[key], list):
                    __ensure_text(element[key])
                    continue


def resolve_labeling_session(
    project_id: str, user_id: str, session_id: str
) -> UserSessions:

    user_session = __collect_user_session_data_from_db(project_id, session_id, user_id)
    if not user_session.session_record_ids:
        collect_user_session_record_ids(user_session, project_id)

    return user_session


def collect_user_session_record_ids(
    user_session: UserSessions, project_id: str
) -> None:
    # currently fixed values. In the future this might be changed to a dynamic value
    limit = 1000
    offset = 0

    # create_notification(
    #     NotificationType.COLLECTING_SESSION_DATA, user_session.created_by, project_id,
    # )

    current_count = general.execute_distinct_count(user_session.count_sql_statement)
    if current_count != user_session.last_count and user_session.last_count != -1:
        create_notification(
            NotificationType.SESSION_RECORD_AMOUNT_CHANGED,
            user_session.created_by,
            project_id,
        )
    user_session.last_count = current_count

    if current_count > limit:
        create_notification(
            NotificationType.SESSION_INFO,
            user_session.created_by,
            project_id,
            limit,
        )

    update_query = __build_record_session_update_query(
        user_session.id_sql_statement, limit, offset, user_session.id
    )
    if user_session.random_seed:
        general.execute(f"SELECT setseed({user_session.random_seed});")
    general.execute(update_query)
    user_session.temp_session = False
    general.commit()


def __collect_user_session_data_from_db(
    project_id: str, session_id: str, user_id: str
) -> UserSessions:

    user_query = user_session.get(project_id, session_id)

    # create empty query
    if not user_query:
        session_id = resolve_extended_search(project_id, user_id, [], 1, 0).session_id
        user_query = user_session.get(project_id, session_id)
    if user_query.created_by != user_id:
        create_notification(
            NotificationType.WRONG_USER_FOR_SESSION, user_id, project_id
        )

    return user_query


def __create_default_user_session_object(
    project_id: str,
    user_id: str,
    filter_data: List[Dict[str, Any]],
    count_sql_statement: str,
    last_count: int,
    random_seed: int,
) -> UserSessionData:
    id_sql_statement = ""

    if len(filter_data) == 0:
        id_sql_statement = __basic_id_query(project_id)
    else:
        inner_sql = __build_inner_query(filter_data, project_id, 0, 0, False)
        id_sql_statement = __build_final_query(inner_sql, project_id, False, True)
        order_extention = __get_order_by(filter_data, project_id)

        if order_extention != "":
            id_sql_statement += order_extention
        else:
            id_sql_statement += "ORDER BY db_order"
    return UserSessionData(
        project_id,
        id_sql_statement,
        count_sql_statement,
        last_count,
        user_id,
        random_seed,
    )


def __create_static_user_session_object(
    project_id: str,
    user_id: str,
    id_sql_statement: str,
    count_sql_statement: str,
    last_count: int,
    random_seed: int,
) -> UserSessionData:
    return UserSessionData(
        project_id,
        id_sql_statement,
        count_sql_statement,
        last_count,
        user_id,
        random_seed,
    )


def __write_user_session_entry(user_session_data: UserSessionData) -> str:
    user_session.delete(user_session_data.project_id, user_session_data.created_by)
    session = user_session.create(user_session_data, with_commit=True)
    return session.id


def generate_count_sql(project_id: str, filter_data: List[Dict[str, Any]]) -> str:

    if len(filter_data) == 0:
        return f"""
        SELECT COUNT(*) distinct_count
        FROM record
        WHERE project_id = '{project_id}'
        AND category = '{RecordCategory.SCALE.value}'
        """
    # no limit or offset since we want to count all
    inner_sql = __build_inner_query(filter_data, project_id, 0, 0, True)
    final_sql = __build_final_query(inner_sql, project_id, True, False)
    return final_sql


def generate_select_sql(
    project_id: str,
    filter_data: List[Dict[str, Any]],
    limit,
    offset,
    for_id: Optional[bool] = False,
) -> str:

    if len(filter_data) == 0:
        return __basic_query(project_id, limit, offset)

    inner_sql = __build_inner_query(filter_data, project_id, limit, offset, False)
    final_sql = __build_final_query(inner_sql, project_id, False, for_id)

    order_extention = __get_order_by(filter_data, project_id)

    if order_extention != "":
        final_sql += order_extention
    else:
        final_sql += "ORDER BY db_order"
    return final_sql


def __build_inner_query(
    filter_data: List[Dict[str, Any]],
    project_id: str,
    limit: int,
    offset: int,
    for_count: bool,
) -> str:
    sql = __build_base_query(filter_data, project_id, for_count)
    sql = __add_limit_and_offset(sql, limit, offset)
    return sql


def __build_base_query(
    filter_data: List[Dict[str, Any]], project_id: str, for_count: bool
) -> str:
    select_add = ""
    from_add = ""
    where_add = ""
    if for_count:
        order_by_add = ""
    else:
        order_by_add = __get_order_by(filter_data, project_id)

    where_add = __build_where_add(filter_data)

    tmp_selection_add, tmp_from_add = __build_subquery_data(
        filter_data, project_id, "WHITELIST"
    )
    select_add += tmp_selection_add
    from_add += tmp_from_add

    tmp_where_add, tmp_from_add = __build_subquery_data(
        filter_data, project_id, "BLACKLIST"
    )
    where_add += tmp_where_add
    from_add += tmp_from_add

    if order_by_add != "":
        tmp_selection_add, tmp_from_add = __get_order_by_subquery(
            filter_data, project_id
        )
        select_add += tmp_selection_add
        from_add += tmp_from_add
    else:
        select_add += ", ROW_NUMBER() OVER() db_order"

    # final build
    base_sql = get_query_template(SearchQueryTemplate.BASE_QUERY)
    base_sql = base_sql.replace("@@SELECT_ADD@@", select_add)
    base_sql = base_sql.replace("@@FROM_ADD@@", from_add)
    base_sql = base_sql.replace("@@WHERE_ADD@@", where_add)
    base_sql = base_sql.replace("@@ORDER_BY_ADD@@", order_by_add)

    base_sql = base_sql.replace("@@PROJECT_ID@@", project_id)

    # format a bit
    base_sql = base_sql.replace("\n\n", "\n")
    base_sql = base_sql.replace("\n", "\n            ")

    return base_sql


def __build_subquery_data(
    filter_data: List[Dict[str, Any]], project_id: str, type_key: str
) -> Tuple[str, str]:
    c = 1
    select_add = ""
    from_add = ""
    where_add = ""

    queries = __get_subqueries(filter_data, type_key)
    for query in queries:
        alias = type_key[0] + "L_" + str(c)
        query_text = __build_subquery(query, project_id, 1)
        if type_key == "WHITELIST":
            select_add += f", {alias}.*"
            from_add += f"""
INNER JOIN ( {query_text} ) {alias}
	ON r.project_id = {alias}.pID AND r.id = {alias}.rID"""
        else:
            where_add += f"\n    AND {alias}.rID IS NULL"
            from_add += f"""
LEFT JOIN ( {query_text} ) {alias}
	ON r.project_id = {alias}.pID AND r.id = {alias}.rID"""
        c += 1

    if type_key == "WHITELIST":
        return select_add, from_add
    else:
        return where_add, from_add


def __build_subquery(
    query_data: List[Dict[str, Any]], project_id: str, depth: int
) -> str:

    final_query = ""

    for filter_element in query_data:
        query_template_key = SearchQueryTemplate[
            filter_element[FilterDataDictKeys.QUERY_TEMPLATE.value]
        ]
        tmp_query = build_query_template(
            query_template_key,
            filter_element[FilterDataDictKeys.VALUES.value],
            project_id,
        )
        if final_query != "":
            final_query += "\nUNION "
        final_query += tmp_query

    final_query = final_query.replace("\n", "\n" + ("    " * depth))

    return final_query


def __build_where_add(
    filter_data: List[Dict[str, Any]], outer: Optional[bool] = True
) -> str:
    current_condition = ""
    for filter_element in filter_data:
        ret = ""
        if FilterDataDictKeys.OPERATOR.value in filter_element:
            ret = build_search_condition(filter_element)

        if FilterDataDictKeys.FILTER.value in filter_element:
            ret = __build_where_add(
                filter_element[FilterDataDictKeys.FILTER.value], False
            )
            if ret != "" and ret[0] != "(":
                ret = f"( {ret} )"
        if ret != "" and filter_element[FilterDataDictKeys.NEGATION.value]:
            ret = f" NOT ( {ret} )"
        if ret != "" and filter_element[FilterDataDictKeys.RELATION.value] != "NONE":
            ret = f" {filter_element[FilterDataDictKeys.RELATION.value]} {ret} "
        current_condition += ret

    if current_condition != "" and outer:
        current_condition = f" AND ({current_condition})"

    return current_condition


def __get_subqueries(filter_data: List[Dict[str, Any]], type_key: str) -> List[Any]:
    to_return = []
    for filter_element in filter_data:
        if FilterDataDictKeys.SUBQUERIES.value in filter_element:
            if filter_element[FilterDataDictKeys.SUBQUERY_TYPE.value] == type_key:
                to_return.append(filter_element[FilterDataDictKeys.SUBQUERIES.value])

    return to_return


def __get_order_by_subquery(
    filter_data: List[Dict[str, Any]], project_id: str
) -> Tuple[str, str]:
    for filter_element in filter_data:
        if FilterDataDictKeys.ORDER_BY.value in filter_element:
            return __build_order_by_subquery(filter_element, project_id)
    return "", ""


def __build_order_by_subquery(
    filter_element: Dict[str, str], project_id: str
) -> Tuple[str, str]:
    order_subqueries = []
    random_requested = False
    select_append = ""
    for column, direction in zip(
        filter_element[FilterDataDictKeys.ORDER_BY.value],
        filter_element[FilterDataDictKeys.ORDER_DIRECTION.value],
    ):
        if column == "RANDOM":
            random_requested = True
            continue
        tmp = build_order_by_table_select(column, direction)
        if tmp == "RECORD":
            data_type = attribute.get_data_type(project_id, column.split("@")[1])
            select_append += ", " + build_order_column_record_data(column, data_type)
        elif tmp:
            order_subqueries.append(tmp)

    order_subqueries = sorted(order_subqueries, key=lambda i: i["TABLE"])

    sql_columns = ""
    table = ""
    return_query = ""
    for order_subquery in order_subqueries:
        if order_subquery["TABLE"] != table and table != "" and sql_columns != "":
            template = get_query_template(order_subquery["TEMPLATE_KEY"])
            template = template.replace("@@ORDER_COLUMNS@@", sql_columns)
            return_query += template
            table = order_subquery["TABLE"]
            sql_columns = ""

        if sql_columns != "":
            sql_columns += ", "
        sql_columns += order_subquery["COL_TEXT"]
        select_append += ", " + order_subquery["SELECT_APPEND"]

    if sql_columns != "":
        template = get_query_template(order_subquery["TEMPLATE_KEY"])
        template = template.replace("@@ORDER_COLUMNS@@", sql_columns)
        return_query += template

    if random_requested:
        select_append += ", RANDOM() rnd_order"

    return select_append, return_query


def __get_order_by(filter_data: List[Dict[str, str]], project_id: str) -> str:

    for filter_element in filter_data:
        if FilterDataDictKeys.ORDER_BY.value in filter_element:
            return __build_order_by(filter_element, project_id)
    return ""


def __build_order_by(filter_element: Dict[str, str], project_id: str) -> str:
    global __seed_number

    order_statement = ""

    for column, direction in zip(
        filter_element[FilterDataDictKeys.ORDER_BY.value],
        filter_element[FilterDataDictKeys.ORDER_DIRECTION.value],
    ):
        if order_statement != "":
            order_statement += ", "
        if "@" in column:
            order_statement += build_order_by_record_data(column, direction)
        elif column == "RANDOM":
            __seed_number = __string_to_postgres_seed(direction)
            order_statement += "rnd_order"
        else:
            order_statement += build_order_by_column(column, direction)

    if order_statement != "":
        return f"""ORDER BY {order_statement}"""

    return order_statement


def __build_final_query(
    inner_select: str, project_id: str, for_count: bool, for_id: bool
) -> str:

    if for_count:
        return f"""
        SELECT COUNT(*) distinct_count
        FROM ( {inner_select} ) id_grabber
        """
    else:
        if for_id:
            return f"""
        SELECT id_grabber.record_id
        FROM ( {inner_select} ) id_grabber
        """
        else:
            return f"""
        SELECT r.*, id_grabber.*, data_grabber.rla_data
        FROM ( {inner_select} ) id_grabber
        INNER JOIN record r
            ON r.id = id_grabber.record_id 
            AND r.project_id = id_grabber.project_id 
        LEFT JOIN (
            SELECT project_id data_pID, record_id data_rID, json_agg(row_to_json(record_label_association)) rla_data
            FROM record_label_association
            WHERE project_id = '{project_id}'
            GROUP BY project_id, record_id
        ) data_grabber
            ON id_grabber.record_id = data_grabber.data_rID 
            AND id_grabber.project_id = data_grabber.data_pID
        WHERE r.project_id = '{project_id}'
        """


def __build_record_session_update_query(
    inner_select: str, limit: int, offset: int, session_id: str
) -> str:
    if limit != 0:
        inner_select += f"\n LIMIT {limit}"
        if offset != 0:
            inner_select += f" OFFSET {offset}"

    return f"""
UPDATE user_sessions SET session_record_ids = (SELECT json_agg(record_id) 
FROM ( {inner_select} ) r) WHERE id = '{session_id}' """


def __basic_query(
    project_id: str,
    limit: int,
    offset: int,
    slice_id: Optional[str] = None,
    order_by: Optional[str] = None,
    select_add: Optional[str] = None,
    from_add: Optional[str] = None,
) -> str:

    sql = __select_record_data(project_id, slice_id, order_by, select_add, from_add)
    sql = __add_limit_and_offset(sql, limit, offset)
    sql = __select_full_extended_search(project_id, sql, order_by)
    return sql


def __select_full_extended_search(project_id: str, sql: str, order_by: str) -> str:
    if not order_by:
        order_by = "ORDER BY db_order"
    return f"""
    SELECT r.*,data_grabber.rla_data
    FROM ({sql}) r
    LEFT JOIN (
        SELECT project_id data_pID, record_id data_rID, json_agg(row_to_json(record_label_association)) rla_data
        FROM record_label_association
        WHERE project_id = '{project_id}'
        GROUP BY project_id, record_id
    ) data_grabber
        ON r.id = data_grabber.data_rID 
        AND r.project_id = data_grabber.data_pID
    {order_by}
    """


def __select_record_data(
    project_id: str,
    slice_id: Optional[str] = None,
    order_by: Optional[str] = None,
    select_add: Optional[str] = None,
    from_add: Optional[str] = None,
) -> str:
    if not order_by:
        order_by = "ORDER BY db_order"
    if not select_add:
        select_add = ", ROW_NUMBER() OVER() db_order"
    sql = f"""
        SELECT r.*, r.id as record_id {select_add}
        FROM record r
        """
    if slice_id:
        sql += __join_dsra_on_slice_id(project_id, slice_id)
    if from_add:
        sql += from_add
    sql += f"WHERE r.project_id = '{project_id}' "
    if not slice_id:
        sql += f"AND r.category = '{RecordCategory.SCALE.value}' "

    sql += "\n" + order_by
    return sql


def __basic_id_query(project_id: str) -> str:
    return f"""
        SELECT r.id record_id
        FROM record r
        WHERE r.project_id = '{project_id}'
        AND r.category = '{RecordCategory.SCALE.value}'
        """


def __add_data_slice_id_and_project_id_column(
    sql: str, data_slice_id: str, project_id: str
) -> str:
    return sql.replace(
        "SELECT id_grabber.record_id",
        f"SELECT '{data_slice_id}' as data_slice_id, id_grabber.record_id, '{project_id}' as project_id",
    )


def __add_insert_into_dsra_statement(sql: str) -> str:
    return f"INSERT INTO {Tablenames.DATA_SLICE_RECORD_ASSOCIATION.value}{sql}"


def __add_limit_and_offset(sql: str, limit: int, offset: int) -> str:
    if limit != 0:
        sql += f"\nLIMIT {limit} "
    if offset != 0:
        sql += f"OFFSET {offset} "
    return sql


def __join_dsra_on_slice_id(project_id: str, slice_id: str) -> str:
    return f"""INNER JOIN data_slice_record_association dsra
                ON dsra.project_id = '{project_id}' AND dsra.data_slice_id = '{slice_id}' AND r.id = dsra.record_id AND r.project_id = dsra.project_id
                """


def __count_dsra(slice_id: str) -> str:
    return f"""
        SELECT COUNT(*) distinct_count
        FROM data_slice_record_association dsra
        WHERE dsra.data_slice_id = '{slice_id}'
        """


def __string_to_postgres_seed(seed_str: str) -> float:
    adler = zlib.adler32(bytes(seed_str, "utf-8"))
    return (adler / 0xFFFFFFFF) - 0.5
