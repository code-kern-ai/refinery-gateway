from ast import Str
from typing import Any, Dict, List
from controller.tokenization.manager import get_token_dict_for_records
from submodules.model.business_objects import attribute

import pandas as pd
from submodules.model import enums
from submodules.model.business_objects import user
from util.miscellaneous_functions import chunk_list


from controller.auth import kratos

from . import enums as ls_enums
from submodules.model.business_objects import project

ID_HELPER_IDX = "id_helper_index"
HAS_EXTRACTION_DATA = "has_extraction_data"


def parse_dataframe_data(project_id: str, df: pd.DataFrame) -> pd.DataFrame:
    column_info = {c: __get_column_info(c) for c in df.columns}
    user_email_lookup = __get_user_email_lookup(project_id)
    attribute_fallback = __get_attribute_fallback_name(project_id)
    token_lookup = __get_token_lookup(project_id, df, column_info)

    df[ID_HELPER_IDX] = range(0, len(df) * 100, 100)
    df["l_studio"] = df.apply(
        lambda row: __parse_pandas_row(
            row, user_email_lookup, column_info, attribute_fallback, token_lookup
        ),
        axis=1,
    )

    return df["l_studio"]


def __get_token_lookup(
    project_id: str,
    df: pd.DataFrame,
    column_info: Dict[Any, Dict[str, Any]],
) -> Dict[str, Dict[str, List[int]]]:
    # record_id -> attribute_name -> [ {start:token.idx, end:token.idx + len(token)}]
    extraction_column_list = [
        column_info[c]["name"]
        for c in column_info
        if column_info[c]["type"]
        == ls_enums.LabelStudioTypes.ANNOTATION_COLUMN_EXTRACTION
    ]
    df[HAS_EXTRACTION_DATA] = df.apply(
        lambda row: row[extraction_column_list].any(), axis=1
    )
    record_ids = df.loc[df[HAS_EXTRACTION_DATA], "record_id"].tolist()
    lookup_list = {}
    for record_pack in chunk_list(record_ids):
        lookup_list |= get_token_dict_for_records(project_id, record_pack)

    return lookup_list


def __get_attribute_fallback_name(project_id: str) -> str:
    # used for "full record" tasks without attribute context
    # -> not possible in label studio so first text attribute is used
    attributes = attribute.get_all_ordered(project_id, True)
    for att in attributes:
        if att.data_type == enums.DataTypes.TEXT.value:
            return att.name

    return "Unknown"


def __get_user_email_lookup(project_id: str) -> Dict[str, Dict[str, str]]:
    org_id = project.get(project_id).organization_id
    users = user.get_all(org_id)
    return {str(u.id): kratos.resolve_user_mail_by_id(u.id) for u in users}


def __get_column_info(column: Any) -> Dict[Str, Any]:
    return {"type": __assume_column_type(str(column)), "name": str(column)}


def __assume_column_type(column_name: str) -> ls_enums.LabelStudioTypes:
    if column_name in ["record_id", ID_HELPER_IDX]:
        return ls_enums.LabelStudioTypes.PROTECTED_COLUMN
    elif column_name.endswith("__created_by") or column_name.endswith("__token_info"):
        # classification label columns only needed for label studio parse
        return ls_enums.LabelStudioTypes.PROTECTED_COLUMN
    elif column_name.endswith("__task_data"):
        return ls_enums.LabelStudioTypes.ANNOTATION_COLUMN_EXTRACTION
    elif "__" in column_name:
        return ls_enums.LabelStudioTypes.ANNOTATION_COLUMN_CLASSIFICATION
    else:
        return ls_enums.LabelStudioTypes.DATA_COLUMN


def __parse_pandas_row(
    row: pd.Series,
    user_email_lookup: Dict[str, Dict[str, str]],
    column_info: Dict[Any, Dict[str, Any]],
    attribute_fallback: str,
    token_lookup: Dict[str, Dict[str, List[int]]],
):
    # row.columns
    return_value = {
        "data": __build_data_set(row, column_info),
        "annotations": __build_annotations_list(
            row, user_email_lookup, column_info, attribute_fallback, token_lookup
        ),
    }
    # print(return_value)

    return return_value


def __build_data_set(
    row: pd.Series, column_info: Dict[Any, Dict[str, Any]]
) -> Dict[str, Any]:
    return_value = {}
    for c in column_info:
        if column_info[c]["type"] == ls_enums.LabelStudioTypes.DATA_COLUMN:
            return_value[column_info[c]["name"]] = row[column_info[c]["name"]]
    return return_value


def __build_annotations_list(
    row: pd.Series,
    user_email_lookup: Dict[str, Dict[str, str]],
    column_info: Dict[Any, Dict[str, Any]],
    attribute_fallback: str,
    token_lookup: Dict[str, Dict[str, List[int]]],
) -> List[Dict[str, Any]]:
    return_value = []
    id_add = 0
    for c in column_info:
        if not row[c]:
            continue
        if (
            column_info[c]["type"]
            == ls_enums.LabelStudioTypes.ANNOTATION_COLUMN_CLASSIFICATION
        ):
            # build annotation head
            user_id = row[column_info[c]["name"] + "__created_by"]
            head = __build_annotation_head(
                row, user_email_lookup, id_add, user_id, column_info[c]["name"]
            )
            head["result"].append(
                __build_annotation_result_classification(
                    row, column_info[c]["name"], attribute_fallback
                )
            )
            return_value.append(head)
            id_add += 1
        elif (
            column_info[c]["type"]
            == ls_enums.LabelStudioTypes.ANNOTATION_COLUMN_EXTRACTION
        ):

            for rla in row[column_info[c]["name"]]:
                user_id = rla["rla_data"]["created_by"]
                head = __build_annotation_head(
                    row, user_email_lookup, id_add, user_id, column_info[c]["name"]
                )
                head["result"].append(
                    __build_annotation_result_extraction(
                        row, column_info[c]["name"], token_lookup, rla
                    )
                )
                return_value.append(head)
                id_add += 1

    return return_value


def __build_annotation_head(
    row: pd.Series,
    user_email_lookup: Dict[str, Dict[str, str]],
    id_add: int,
    user_id: str,
    col_name: str,
) -> Dict[str, Any]:
    mail = "Unknown"
    if user_id in user_email_lookup:
        mail = user_email_lookup[user_id]
    return_value = {
        "id": row[ID_HELPER_IDX] + id_add,
        "created_username": mail,
        "completed_by": {
            "id": user_id,
            "email": mail,
        },
        "__kern_source": col_name,
        "result": [],
    }
    return return_value


def __build_annotation_result_classification(
    row: pd.Series, label_col_name: str, attribute_fallback: str
) -> Dict[str, Any]:
    parts = label_col_name.split("__")
    attribute_name = parts[0]
    if attribute_name == "":
        attribute_name = attribute_fallback

    return {
        "from_name": parts[1],
        "to_name": attribute_name,
        "type": ls_enums.LabelStudioTypes.CHOICES.value,
        "origin": ls_enums.LabelStudioTypes.MANUAL.value,
        "value": {"choices": [row[label_col_name]]},
    }


def __build_annotation_result_extraction(
    row: pd.Series,
    label_col_name: str,
    token_lookup: Dict[str, Dict[str, List[int]]],
    rla: Dict[str, Any],
) -> Dict[str, Any]:
    parts = label_col_name.split("__")
    token = rla["rla_data"]["token"]
    start_token = token[0]
    end_token = token[-1]

    return {
        "value": {
            "start": token_lookup[row["record_id"]][parts[0]][start_token]["start"],
            "end": token_lookup[row["record_id"]][parts[0]][end_token]["end"],
            "labels": [rla["rla_data"]["label_name"]],
        },
        "id": rla["rla_id"],
        "from_name": parts[1],
        "to_name": parts[0],
        "type": ls_enums.LabelStudioTypes.LABELS.value,
        "origin": ls_enums.LabelStudioTypes.MANUAL.value,
    }
