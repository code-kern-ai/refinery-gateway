from typing import Tuple, List, Union, Dict
from controller.misc.config_service import get_config_value

from controller.transfer import util as transfer_util
from controller.transfer.valid_arguments import valid_arguments
import pandas as pd
from util.notification import create_notification
from submodules.model.enums import NotificationType
from submodules.model.business_objects import attribute, record, general
from controller.labeling_task.util import infer_labeling_task_name
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def run_checks(df: pd.DataFrame, project_id, user_id) -> None:
    guard = False
    errors = {}
    columns = df.columns

    # check if columns are unique
    columns_duplicated = columns.duplicated()
    duplicated_columns = [
        column for idx, column in enumerate(columns) if columns_duplicated[idx]
    ]
    if duplicated_columns:
        guard = True

        notification = create_notification(
            NotificationType.DUPLICATED_COLUMNS,
            user_id,
            project_id,
            duplicated_columns,
        )

        errors["DuplicatedKey"] = notification.message
    # split columns into categories
    attributes = []
    target_attributes = []
    task_names = []
    for column in columns:
        if column.startswith("__"):
            task_names.append(infer_labeling_task_name(column))
        elif "__" in column:
            target_attributes.append(transfer_util.infer_attribute(column))
            task_names.append(infer_labeling_task_name(column))
        else:
            attributes.append(transfer_util.infer_attribute(column))

    # check duplicated task names
    duplicated_task_names = set()
    task_names_set = set()
    for task_name in task_names:

        if task_name in task_names_set:
            duplicated_task_names.add(task_name)
        else:
            task_names_set.add(task_name)

    if duplicated_task_names != set():
        guard = True
        notification = create_notification(
            NotificationType.DUPLICATED_TASK_NAMES,
            user_id,
            project_id,
            list(duplicated_task_names),
        )
        errors["DuplicatedTaskNames"] = notification.message

    # check attribute equality
    attribute_entities = attribute.get_all(project_id)
    attribute_names = [attribute_item.name for attribute_item in attribute_entities]
    differences = set(attribute_names).difference(set(attributes))
    if differences:
        guard = True
        notification = create_notification(
            NotificationType.DIFFERENTIAL_ATTRIBUTES,
            user_id,
            project_id,
            list(differences),
        )
        errors["DifferentialAttributes"] = notification.message

    # check target attributes exists or are in file
    non_existing_targets = (
        set(target_attributes)
        .difference(set(attributes))
        .difference(set(attribute_names))
    )

    if non_existing_targets != set():
        guard = True
        notification = create_notification(
            NotificationType.NON_EXISTENT_TARGET_ATTRIBUTE,
            user_id,
            project_id,
            list(non_existing_targets),
        )
        errors["NonExistentTargetAttributes"] = notification.message

    # check if composite key constraint is not hurt
    primary_key_names = [
        attribute_item.name
        for attribute_item in attribute_entities
        if attribute_item.is_primary_key
    ]
    if primary_key_names:
        concatenated_primary_keys = (
            df[primary_key_names].astype(str).apply("-".join, axis=1)
        )
        duplicated_composite_keys = df.loc[concatenated_primary_keys.duplicated(), :]
        if not duplicated_composite_keys.empty:
            guard = True
            notification = create_notification(
                NotificationType.DUPLICATED_COMPOSITE_KEY, user_id, project_id
            )
            errors["DuplicatedCompositeKeys"] = notification.message
    if guard:
        logger.error(errors)
        raise Exception(str(errors))


def run_limit_checks(df: pd.DataFrame, project_id, user_id) -> None:
    limits = get_config_value("limit_checks")
    guard = False
    errors = {}
    if df.shape[0] > limits["max_rows"]:
        guard = True
        notification = create_notification(
            NotificationType.NEW_ROWS_EXCEED_MAXIMUM_LIMIT,
            user_id,
            project_id,
            df.shape[0],
            limits["max_rows"],
        )
        errors["MaxRows"] = notification.message
    else:
        count_current_records = record.count(project_id)
        if count_current_records:
            updating = get_update_amount(df, project_id)
            if count_current_records - updating + df.shape[0] > limits["max_rows"]:
                guard = True
                notification = create_notification(
                    NotificationType.TOTAL_ROWS_EXCEED_MAXIMUM_LIMIT,
                    user_id,
                    project_id,
                    count_current_records - updating + df.shape[0],
                    limits["max_rows"],
                )
                errors["MaxRows"] = notification.message

    if df.shape[1] > limits["max_cols"]:
        guard = True
        notification = create_notification(
            NotificationType.COLS_EXCEED_MAXIMUM_LIMIT,
            user_id,
            project_id,
            df.shape[1],
            limits["max_cols"],
        )
        errors["MaxCols"] = notification.message
    max_length_dict = dict(
        [
            (v, df[v].apply(lambda r: len(str(r)) if r != None else 0).max())
            for v in df.columns.values
        ]
    )

    for key in max_length_dict:
        if max_length_dict[key] > limits["max_char_count"]:
            guard = True
            notification = create_notification(
                NotificationType.COL_EXCEED_MAXIMUM_LIMIT,
                user_id,
                project_id,
                key,
                max_length_dict[key],
                limits["max_char_count"],
            )
            errors["MaxLength"] = notification.message

    if guard:
        # no need to check further
        logger.error(errors)
        raise Exception(str(errors))


def build_df_sql(project_id: str) -> Tuple[str, List[str]]:
    primary_keys = attribute.get_primary_keys(project_id)
    if not primary_keys:
        return None, None
    sql = "SELECT id record_id"
    keys = []
    for att in primary_keys:
        sql += f", r.data->>'{att.name}' {att.name}"
        keys.append(att.name)
    sql += f"\nFROM record r WHERE project_id = '{project_id}'"
    return sql, keys


def check_argument_allowed(arg: str) -> bool:
    return arg in valid_arguments


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
                create_notification(
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


def get_update_amount(df: pd.DataFrame, project_id: str) -> int:
    updating = 0
    sql, keys = build_df_sql(project_id)
    if sql:
        sql_df = pd.read_sql(sql, con=general.get_bind())
        for column in keys:
            if not column in df.columns:
                return 0
            type_name = df[column].dtype.name
            if type_name in ["int64", "float64", "bool"]:
                sql_df[column] = sql_df[column].astype(type_name)

        updating = pd.merge(left=df[keys], right=sql_df, on=keys).shape[0]
    return updating
