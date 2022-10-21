# function to be delted after full merge


from submodules.model.business_objects import general

import pandas as pd
import numpy as np
from submodules.model.business_objects.export import OUTSIDE_CONSTANT

from util.sql_helper import parse_sql_text


def dummy():
    COLUMN_NAME_INPUT = "record_data_manual"
    COLUMN_NAME_FINAL = "headline__indicators__MANUAL"
    MAX_LABEL_SIZE = "50"  # this should be max(len(lt.name))+2 || len(OUTSIDE_CONSTANT) -- (whichever is bigger)
    PROJECT_ID = "7ef32415-cf08-42e3-b7a8-cfdcc2531f82"

    df = __get_record_data_dummy(PROJECT_ID, COLUMN_NAME_INPUT)
    df[COLUMN_NAME_FINAL] = df.apply(
        lambda row: parse_row_current(row, COLUMN_NAME_INPUT, MAX_LABEL_SIZE), axis=1
    )

    has_confidence = __has_confidence(df, COLUMN_NAME_INPUT)
    if has_confidence:
        df[COLUMN_NAME_FINAL + "__confidence"] = df.apply(
            lambda row: parse_row_current_confidence(row, COLUMN_NAME_INPUT), axis=1
        )
    df = df.drop(COLUMN_NAME_INPUT, axis="columns")
    df.to_csv("tmp/myfile.csv", index=False)
    df.to_json("tmp/myfile.json", orient="records")


def __has_confidence(df: pd.DataFrame, data_col_name: str) -> bool:
    # first row, column data_col_name -> holds list of dicts ->first element -> key "rla_data" -> key "confidence"
    return df.loc[0][data_col_name][0]["rla_data"]["confidence"] != None


def parse_row_current(row: pd.Series, data_col_name: str, max_string_size: str):
    record_data = row[data_col_name]
    token_count = record_data[0]["rla_data"]["token_count"]
    arr = np.full(token_count, OUTSIDE_CONSTANT, dtype="<U" + max_string_size)
    for rla in record_data:
        for idx, token in enumerate(rla["rla_data"]["token"]):
            if idx == 0:
                arr[token] = "B-" + rla["rla_data"]["label_name"]
            else:
                arr[token] = "I-" + rla["rla_data"]["label_name"]
    return arr


def parse_row_current_confidence(row: pd.Series, data_col_name: str):
    record_data = row[data_col_name]
    token_count = record_data[0]["rla_data"]["token_count"]
    arr_confidence = np.full(token_count, 0, dtype=np.float16)
    for rla in record_data:
        for token in rla["rla_data"]["token"]:
            arr_confidence[token] = rla["rla_data"]["confidence"]

    return arr_confidence


def __get_record_data_dummy(
    project_id: str, data_column_name: str
) -> pd.DataFrame:  # List[Dict[str,Any]]:
    query = f"""
    SELECT 
        extract_data_grabber.record_id::TEXT,
        extract_data_grabber.project_id::TEXT,
        array_agg(
            json_build_object(
            'rla_id',extract_data_grabber.rla_id,
            'rla_data',extract_data_grabber.rla_data)) {data_column_name}
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
        WHERE rla.return_type = 'YIELD' --ensure extraction
        AND rla.project_id ='{project_id}'
        AND rla.source_type = 'MANUAL' 
            AND rla.is_valid_manual_label --only for manual
    ) extract_data_grabber
    --WHERE record_id = '169cd92f-9f6f-42e6-be9e-225b37df69e1'
    GROUP BY extract_data_grabber.record_id, extract_data_grabber.project_id
    """
    # sql_df = pd.read_sql(parse_sql_text(query), con=general.get_bind())
    return pd.read_sql(parse_sql_text(query), con=general.get_bind())
    return general.execute_all(query)
