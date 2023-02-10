import os
from typing import List, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd

from controller.transfer.checks import run_checks, run_limit_checks

__engine = None


async def unpack_request_body(request_body):
    user_id = request_body.query_params["user_id"]
    request_body = await request_body.json()
    name = request_body["name"]
    description = request_body["description"]
    tokenizer = request_body["tokenizer"]
    store_id = request_body["store_id"]
    return user_id, name, description, tokenizer, store_id


def get_workflow_db_engine():
    global __engine
    if __engine is None:
        __engine = create_engine(os.getenv("WORKFLOW_POSTGRES"))
    return __engine


def get_records_from_store(store_id: str) -> List[Dict[str, Any]]:
    Session = sessionmaker(get_workflow_db_engine())
    with Session() as session:
        record_entity_list = session.execute(
            f"SELECT record FROM store_entry WHERE store_id = '{store_id}'"
        ).all()

    record_dict_list = [result for result, in record_entity_list]
    return record_dict_list


def check(data, project_id, user_id):
    df = pd.DataFrame(data)
    run_checks(df, project_id, user_id)
    run_limit_checks(df, project_id, user_id)
