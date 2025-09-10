from submodules.model.global_objects import admin_queries as admin_queries_db_go
from submodules.model.enums import AdminQueries
import json
from submodules.model.util import sql_alchemy_to_dict


def test_full_admin_queries():
    """
    Test validate user is an administrator

    Args:
        client (TestClient): The test client for making API requests.
    """

    for query in AdminQueries:
        data = admin_queries_db_go.get_result_admin_query(
            query, __get_default_filter_for_admin_query(query)
        )
        assert isinstance(
            data, list
        ), f"Response is not a list for query: {query.value}"
        print(
            f"Query {query.value} returned ",
            json.dumps(sql_alchemy_to_dict(data), indent=2, default=str),
            flush=True,
        )


def __get_default_filter_for_admin_query(query: AdminQueries) -> dict:
    # USERS_TO_PROJECTS, USERS_BY_ORG
    # AVG_MESSAGES_PER_CONVERSATION_GLOBAL, CREATED_TAGS_PER_ORG
    if query in (
        AdminQueries.USERS_TO_PROJECTS,
        AdminQueries.USERS_BY_ORG,
        AdminQueries.AVG_MESSAGES_PER_CONVERSATION_GLOBAL,
        AdminQueries.CREATED_TAGS_PER_ORG,
    ):
        return {
            "organization_id": "",
            "without_kern_email": False,
        }

    # ACTIVE_USERS_GLOBAL, ACTIVE_USERS_BY_ORG
    elif query in (AdminQueries.ACTIVE_USERS_GLOBAL, AdminQueries.ACTIVE_USERS_BY_ORG):
        return {
            "min_msg_count": 1,
            "period": "days",
            "slices": 7,
            "organization_id": "",
            "without_kern_email": False,
        }

    # MESSAGES_CREATED, MESSAGES_CREATED_BY_PROJECT, MESSAGES_FEEDBACK_PER_PROJECT
    elif query in (
        AdminQueries.MESSAGES_CREATED,
        AdminQueries.MESSAGES_CREATED_BY_PROJECT,
        AdminQueries.MESSAGES_FEEDBACK_PER_PROJECT,
    ):
        return {
            "period": "days",
            "slices": 7,
            "organization_id": "",
            "without_kern_email": False,
        }

    # AVG_MESSAGES_PER_CONVERSATION, MACRO_EXECUTIONS
    elif query in (
        AdminQueries.AVG_MESSAGES_PER_CONVERSATION,
        AdminQueries.MACRO_EXECUTIONS,
    ):
        return {
            "period": "days",
            "slices": 7,
            "organization_id": "",
            "without_kern_email": False,
        }

    # FOLDER_MACRO_EXECUTION_SUMMARY
    elif query is AdminQueries.FOLDER_MACRO_EXECUTION_SUMMARY:
        return {
            "slices": 7,
            "organization_id": "",
        }

    else:
        raise ValueError(f"Unknown admin query: {query}")
