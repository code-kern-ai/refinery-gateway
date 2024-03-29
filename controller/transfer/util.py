import datetime
import json
from typing import Any, List, Dict, Tuple, Union, Optional

from submodules.model import enums
from .checks import check_argument_allowed, run_checks, run_limit_checks
from submodules.model.models import UploadTask
import pandas as pd
from submodules.model.enums import NotificationType
from submodules.model.business_objects import record
import os
import logging
import traceback
from util import category
from util import notification

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_upload_task_message(
    task: UploadTask,
    include_duration: Optional[bool] = True,
    additional_information: str = "",
) -> str:
    message = f"Upload Task. ID: {task.id} Project ID: {task.project_id}. State: {task.state}. Progress: {task.progress}. Started at: {task.started_at}."
    message = (
        message + f"Finished at: {task.finished_at}." if task.finished_at else message
    )
    message = (
        message + f"Duration: {datetime.datetime.now() - task.started_at}."
        if include_duration
        else message
    )
    message = (
        f"{message} {additional_information}"
        if additional_information != ""
        else message
    )
    return message


def read_file_to_df(
    file_type: str,
    file_path: str,
    user_id: str,
    file_import_options: str,
    project_id: str,
) -> pd.DataFrame:
    if not os.path.exists(file_path):
        raise Exception("Couldn't locate file")

    file_type = file_type.lower()
    if file_type in ["xls", "xlsm", "xlsb", "odf", "ods", "odt"]:
        file_type = "xlsx"

    file_import_options = (
        string_to_import_option_dict(file_import_options, user_id, project_id)
        if file_import_options
        else {}
    )
    try:
        if file_type in ["csv", "txt", "text"]:
            df = pd.read_csv(file_path, **file_import_options)
        elif file_type == "xlsx":
            df = pd.read_excel(file_path, **file_import_options)
        elif file_type == "json":
            df = pd.read_json(file_path, **file_import_options)
        else:
            notification.create_notification(
                NotificationType.INVALID_FILE_TYPE,
                user_id,
                project_id,
                file_type,
            )
            raise Exception("Upload conversion error", "Upload ran into errors")
        # ensure useable columns dont break the import
        df = df.replace("\u0000", " ", regex=True)
        df.fillna(" ", inplace=True)
    except Exception as e:
        logger.error(traceback.format_exc())
        notification.create_notification(
            NotificationType.UPLOAD_CONVERSION_FAILED,
            user_id,
            project_id,
            str(e),
        )
        raise Exception("Upload conversion error", "Upload ran into errors")
    return df


def convert_to_record_dict(
    file_type: str,
    file_name: str,
    user_id: str,
    file_import_options: str,
    project_id: str,
    column_mapping: Optional[Dict[str, str]] = None,
) -> Tuple[List, str]:
    if not file_type:
        notification.create_notification(
            NotificationType.FILE_TYPE_NOT_GIVEN,
            user_id,
            project_id,
        )

        if os.path.exists(file_name):
            os.remove(file_name)
        raise Exception("Upload conversion error", "Upload ran into errors")
    try:
        df = read_file_to_df(
            file_type, file_name, user_id, file_import_options, project_id
        )
    except Exception as e:
        if os.path.exists(file_name):
            os.remove(file_name)
        raise e
    if os.path.exists(file_name):
        os.remove(file_name)

    if column_mapping:
        df.rename(columns=column_mapping, inplace=True)
    run_limit_checks(df, project_id, user_id)
    run_checks(df, project_id, user_id)
    check_and_convert_category_for_unknown(df, project_id, user_id)

    covert_nested_attributes_to_text(df)
    added_col = add_running_id_if_not_present(df, project_id)
    return df.to_dict("records"), added_col


def add_running_id_if_not_present(df: pd.DataFrame, project_id: str) -> Optional[str]:
    record_item = record.get_one(project_id)
    if record_item:
        # project already has records => no extensions of existing data
        return
    has_id_like = False
    for key in df.columns:
        if category.infer_category_enum(df, key) == enums.DataTypes.INTEGER.value:
            has_id_like = True
            break
    if has_id_like:
        return
    col_name = "running_id"
    while col_name in df.columns:
        col_name += "_"
    df[col_name] = df.index

    return col_name


def check_and_convert_category_for_unknown(
    df_check: pd.DataFrame, project_id: str, user_id: str
) -> None:
    changed_keys = []
    for key in df_check.columns:
        if category.infer_category_enum(df_check, key) == enums.DataTypes.UNKNOWN.value:
            changed_keys.append(key)
            df_check[key] = df_check[key].astype(str)
    if len(changed_keys) > 0:
        notification.create_notification(
            NotificationType.UNKNOWN_DATATYPE.value,
            user_id,
            project_id,
            ", ".join(changed_keys),
        )


def covert_nested_attributes_to_text(df: pd.DataFrame) -> pd.DataFrame:
    for key in df.columns:
        sample = pick_sample(df, key)
        if check_sample_has_dict_or_list_values(sample):
            df[key] = df[key].apply(lambda x: json.dumps(x))


def check_sample_has_dict_or_list_values(sample: List[Any]) -> bool:
    for value in sample:
        if isinstance(value, dict) or isinstance(value, list):
            return True
    return False


def pick_sample(df: pd.DataFrame, key: str, sample_size: int = 10) -> pd.Series:
    column_size = len(df[key])
    if column_size <= sample_size:
        return df[key].sample(column_size)

    return df[key].sample(sample_size)


def string_to_import_option_dict(
    import_string: str, user_id: str, project_id: str
) -> Dict[str, Union[str, int]]:
    splitted = import_string.split("\n")
    import_options = {}
    for e in splitted:
        tmp = e.split("=")
        if len(tmp) == 2:
            parameter = tmp[0].strip()
            if not check_argument_allowed(parameter):
                notification.create_notification(
                    NotificationType.UNKNOWN_PARAMETER,
                    user_id,
                    project_id,
                    parameter,
                )
            else:
                import_options[parameter] = tmp[1].strip()
                if import_options[parameter].isdigit():
                    import_options[parameter] = int(import_options[parameter])
    return import_options


def infer_attribute(key: str) -> str:
    seperator_idx = key.find("__")
    return key[:seperator_idx] if seperator_idx != -1 else key
