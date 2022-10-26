# function to be delted after full merge


from typing import Any, Dict, List, Optional, Tuple, Union
from submodules.model.business_objects import attribute, general, project, data_slice

import pandas as pd
import numpy as np
from submodules.model.business_objects.export import OUTSIDE_CONSTANT
from submodules.model import enums
from submodules.model.models import LabelingTask
from util.miscellaneous_functions import first_item, get_max_length_of_task_labels

from util.sql_helper import parse_sql_text


def parse(
    project_id: str,
    final_query: str,
    mapping_dict: Dict[str, str],
    extraction_appends: Dict[str, Union[str, Dict[str, str]]],
    export_options: Dict[str, Any],
):
    df = pd.read_sql(parse_sql_text(final_query), con=general.get_bind())
    df.rename(columns=mapping_dict, inplace=True)

    export_format = export_options.get("format")
    if export_format == enums.RecordExportFormats.DEFAULT.value:
        df = parse_dataframe_data(df, extraction_appends)
        for col in df.columns:
            if str(col).endswith("__created_by"):
                df.drop(col, axis="columns", inplace=True)
    elif export_format == enums.RecordExportFormats.LABEL_STUDIO.value:
        from .labelstudio import export_parser as ls_export_parser

        df = ls_export_parser.parse_dataframe_data(project_id, df)
    else:
        message = f"Format {export_format} not supported."
        raise Exception(message)

    file_type = export_options.get("file_type")
    file_name = infer_file_name(project_id, export_options, export_format)
    file_path = f"tmp/{file_name}"
    if file_type == enums.RecordExportFileTypes.JSON.value:
        df.to_json(file_path, orient="records")
    elif file_type == enums.RecordExportFileTypes.CSV.value:
        df.to_csv(file_path, index=False)
    elif file_type == enums.RecordExportFileTypes.XLSX.value:
        df.to_excel(file_path)
    else:
        message = f"File type {file_type} not supported."
        raise Exception(message)
    return file_path, file_name


def infer_file_name(
    project_id: str, export_options: Dict[str, Any], export_format: str
):
    project_item = project.get(project_id)
    row_option = export_options.get("rows")
    if row_option.get("type") == enums.RecordExportAmountTypes.SLICE.value:
        slice_item = data_slice.get(project_id, row_option.get("id"))
        amount_type_addition = slice_item.name
    else:
        amount_type_addition = row_option.get("type")

    file_name = f"{project_item.name}_{export_format}_{amount_type_addition}".lower()

    if export_options.get("file_type") == enums.RecordExportFileTypes.JSON.value:
        file_name = f"{file_name}.json"
    elif export_options.get("file_type") == enums.RecordExportFileTypes.CSV.value:
        file_name = f"{file_name}.csv"
    elif export_options.get("file_type") == enums.RecordExportFileTypes.XLSX.value:
        file_name = f"{file_name}.xlsx"
    else:
        message = f"File type {export_options.get('file_type')} not supported."
        raise Exception(message)

    return file_name


def parse_dataframe_data(
    df: pd.DataFrame,
    extraction_appends: Dict[str, Union[str, Dict[str, str]]],
) -> pd.DataFrame:
    task_add_info = {}
    df.drop("record_id", axis="columns", inplace=True)
    if not extraction_appends["EX_QUERIES"]:
        return df
    for key in extraction_appends["EX_QUERIES"]:
        task: LabelingTask = extraction_appends["EX_QUERIES"][key]["task"]
        if task.id not in task_add_info:
            task_add_info[task.id] = {
                "MAX_LEN": str(get_max_length_of_task_labels(task)),
            }
        base_name = extraction_appends["EX_QUERIES"][key]["base_name"]

        final_name = base_name
        df[final_name] = df.apply(
            lambda row: __parse_pandas_row_current(
                row, base_name, task_add_info[task.id]["MAX_LEN"]
            ),
            axis=1,
        )
        has_confidence = enums.LabelSource.MANUAL.value not in base_name
        if has_confidence:
            df[final_name + "__confidence"] = df.apply(
                lambda row: __parse_pandas_row_current_confidence(row, base_name),
                axis=1,
            )

        df.drop(base_name + "__token_info", axis="columns", inplace=True)
        df.drop(base_name + "__task_data", axis="columns", inplace=True)
    return df


def __parse_pandas_row_current(
    row: pd.Series, data_col_base_name: str, max_string_size: str
):
    record_data = row[data_col_base_name + "__task_data"]
    if not record_data:
        return None
    token_count = row[data_col_base_name + "__token_info"]["token_count"]
    arr = np.full(token_count, OUTSIDE_CONSTANT, dtype="<U" + max_string_size)
    for rla in record_data:
        for idx, token in enumerate(rla["rla_data"]["token"]):
            if idx == 0:
                arr[token] = "B-" + rla["rla_data"]["label_name"]
            else:
                arr[token] = "I-" + rla["rla_data"]["label_name"]
    return arr


def __parse_pandas_row_current_confidence(row: pd.Series, data_col_base_name: str):
    record_data = row[data_col_base_name + "__task_data"]
    if not record_data:
        return None
    token_count = row[data_col_base_name + "__token_info"]["token_count"]
    arr_confidence = np.full(token_count, 0, dtype=np.float16)
    for rla in record_data:
        for token in rla["rla_data"]["token"]:
            arr_confidence[token] = rla["rla_data"]["confidence"]

    return arr_confidence
