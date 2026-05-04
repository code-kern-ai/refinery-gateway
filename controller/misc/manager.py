from typing import Any, Dict
from submodules.model.global_objects import (
    admin_queries as admin_queries_db_go,
)
from submodules.model import enums
from util.tmp_export_file_cleanup import add_cleanup_task
from uuid import uuid4
import pandas as pd
from submodules.model.util import ensure_sql_text
from submodules.model.business_objects import general


def create_admin_query_excel(
    query: enums.AdminQueries, parameters: Dict[str, Any]
) -> str:

    q = admin_queries_db_go.get_result_admin_query(query, parameters, as_query=True)

    df = pd.read_sql(ensure_sql_text(q), con=general.get_bind())
    tmp_filename = f"tmp/feedback_{uuid4()}.xlsx"
    df.to_excel(tmp_filename, index=False)
    add_cleanup_task(tmp_filename, 5)
    return tmp_filename
