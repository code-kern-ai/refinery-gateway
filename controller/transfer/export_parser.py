# function to be delted after full merge


from typing import Dict, List, Optional, Tuple, Union
from submodules.model.business_objects import attribute, general

import pandas as pd
import numpy as np
from submodules.model.business_objects.export import OUTSIDE_CONSTANT
from submodules.model import enums
from submodules.model.business_objects import labeling_task
from submodules.model.models import LabelingTask
from util.miscellaneous_functions import first_item, get_max_length_of_task_labels

from util.sql_helper import parse_sql_text


def query_builder_dummy():
    # only for testing purposes
    PROJECT_ID = "9aa46111-500a-4db3-b7f8-03d7071da82e"
    tasks = labeling_task.get_all(PROJECT_ID)
    LABELING_TASKS_BY_ID = {str(task.id): task for task in tasks}
    LABEL_SOURCES = [
        {"type": enums.LabelSource.WEAK_SUPERVISION.value, "source_id": None},
        {
            "type": enums.LabelSource.INFORMATION_SOURCE.value,
            "source_id": "78bb3ad4-1d35-4a1a-bfa9-ad33b9a5b931",
            "name": "tmp_func_asdf_sadf_asdf_asdfA_fdadsF_adfADS_FadsF_adfAS_DF",
        },
        {"type": enums.LabelSource.MANUAL.value, "source_id": None},
    ]

    extraction_appends = get_extraction_task_appends(
        PROJECT_ID, LABELING_TASKS_BY_ID, LABEL_SOURCES, True
    )

    final_query = f"""
{extraction_appends["WITH"]}
SELECT 
    r.id::TEXT record_id,
    r.data::json->'running_id' as "running_id",
    r.data::json->'headline' as "headline",
    r.data::json->'communication_style' as "communication_style"
    {extraction_appends["SELECT"]}
FROM RECORD r
{extraction_appends["FROM"]}
WHERE r.project_id = '{PROJECT_ID}'
LIMIT 100
    """

    df = pd.read_sql(parse_sql_text(final_query), con=general.get_bind())
    df.rename(columns=extraction_appends["MAPPING"], inplace=True)
    if False:
        df = parse_dataframe_data(df, extraction_appends)
    else:
        from .labelstudio import export_parser as ls_export_parser

        df = ls_export_parser.parse_dataframe_data(PROJECT_ID, df)

    df.to_csv("tmp/myfile.csv", index=False)
    df.to_json("tmp/myfile.json", orient="records")
    # print(df)


def parse_dataframe_data(
    df: pd.DataFrame,
    extraction_appends: Dict[str, Union[str, Dict[str, str]]],
) -> pd.DataFrame:
    task_add_info = {}
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

        df = df.drop(base_name + "__token_info", axis="columns")
        df = df.drop(base_name + "__task_data", axis="columns")
    return df


def get_extraction_task_appends(
    project_id: str,
    labeling_tasks_by_id: Dict[str, LabelingTask],
    label_sources: List[Dict[str, str]],
    with_user_id: bool = False,
) -> Dict[str, Union[str, Dict[str, str]]]:
    return_values = {
        "WITH": "",
        "SELECT": "",
        "FROM": "",
        "EX_QUERIES": None,
        "MAPPING": {},
    }
    if len(labeling_tasks_by_id) == 0:
        return return_values

    has_extraction = False
    counter = 1
    extraction_queries = {}
    for key in labeling_tasks_by_id:
        if (
            labeling_tasks_by_id[key].task_type
            != enums.LabelingTaskType.INFORMATION_EXTRACTION.value
        ):
            continue
        for source in label_sources:
            ed_part = __get_extraction_data_query_and_select(
                counter,
                labeling_tasks_by_id[key],
                source,
            )
            extraction_queries |= ed_part
            x = first_item(ed_part)
            return_values["SELECT"] += x["SELECT"]
            return_values["FROM"] += x["FROM"]
            return_values["MAPPING"] |= x["MAPPING"]
            counter += 1

        has_extraction = True

    if has_extraction:
        return_values["WITH"] = __get_with_query_extraction_tasks(
            project_id, with_user_id
        )
        return_values["EX_QUERIES"] = extraction_queries
    return return_values


### Query stuff


def __get_extraction_data_query_and_select(
    query_counter: int, task: LabelingTask, source: Dict[str, str]
) -> Dict[str, Tuple[str, str]]:
    source_type = source["type"]
    try:
        source_type_parsed = enums.LabelSource[source_type.upper()]
    except KeyError:
        raise ValueError(f"Invalid comment category: {source_type}")

    on_add = f"AND ed.source_type = '{source_type}'"
    if source_type_parsed == enums.LabelSource.MANUAL:
        on_add += f" AND ed.is_valid_manual_label = TRUE "
    elif source_type_parsed == enums.LabelSource.INFORMATION_SOURCE:
        on_add += f" AND ed.source_id = '{source['source_id']}' "
    else:
        # WEAK_SUPERVISION & MODEL_CALLBACK -> nothing to do
        pass
    query_alias = "ed" + str(query_counter)

    query = f"""LEFT JOIN (
        SELECT ed.record_id, ed.project_id,ed.task_data,ti.token_info
        FROM extraction_data ed
        INNER JOIN token_info ti
            ON ed.record_id = ti.record_id AND ed.project_id = ti.project_id AND ti.attribute_id = ed.attribute_id
            AND ed.task_id = '{str(task.id)}' {on_add}
    ) {query_alias}
        ON {query_alias}.record_id = r.id AND {query_alias}.project_id = r.project_id
    """
    attribute_name = __get_attribute_name_from_task(task)
    base_name = f"{attribute_name}__{task.name}__{source_type}"
    if source_type_parsed == enums.LabelSource.INFORMATION_SOURCE:
        base_name += f"__{source['name']}"

    td_mapping = f"{query_alias}_td"
    ti_mapping = f"{query_alias}_ti"
    mapping = {
        td_mapping: f"{base_name}__task_data",
        ti_mapping: f"{base_name}__token_info",
    }

    select = f""",\n    {query_alias}.task_data \"{td_mapping}\",\n    {query_alias}.token_info \"{ti_mapping}\""""

    return {
        query_alias: {
            "SELECT": select,
            "FROM": query,
            "MAPPING": mapping,
            "base_name": base_name,
            "task": task,
        }
    }


def __get_attribute_name_from_task(task: LabelingTask) -> str:
    return attribute.get(task.project_id, task.attribute_id).name


def __get_with_query_extraction_tasks(
    project_id: str, with_user_id: bool = False
) -> str:
    created_by_add = ""
    if with_user_id:
        created_by_add = ",\n   	         'created_by', rla.created_by"
    return f"""WITH token_info AS (
	SELECT 
		record_id, 
		project_id,
		attribute_id,
		jsonb_build_object(
			'token_count',num_token,
			'char_count',num_char) token_info
	FROM(
		SELECT r.id record_id, r.project_id, a.id attribute_id, rats.num_token, LENGTH(r.data->>a.name) num_char
		FROM attribute a
		INNER JOIN record r
		    ON a.project_id = r.project_id
		INNER JOIN record_attribute_token_statistics rats
		    ON a.project_id = rats.project_id AND a.id = rats.attribute_id AND r.id = rats.record_id
		WHERE a.data_type = '{enums.DataTypes.TEXT.value}'
		AND a.project_id = '{project_id}'
	) i
),
extraction_data AS (
	 SELECT
	     record_id,
	     project_id,
	     source_type,
	     is_valid_manual_label,
	     source_id,
	     task_id,
	     attribute_id,	     
	     array_agg(
	         jsonb_build_object(
	         'rla_id',rla_id,
	         'rla_data',rla_data)) task_data
	 FROM (
	     SELECT
	         rla.record_id,
	         rla.project_id,
	         rla.source_type,
	         rla.is_valid_manual_label,
	         rla.source_id,
	         lt.id task_id,
	         lt.attribute_id,
	         rla.id rla_id,
	         jsonb_build_object(
		         'confidence', CASE WHEN source_type='{enums.LabelSource.MANUAL.value}' THEN NULL ELSE ROUND(rla.confidence::numeric,4) END,
		         'source_type', rla.source_type,
		         'token', token.token,
		         'label_name', ltl.name{created_by_add})rla_data
	     FROM record_label_association rla
	     INNER JOIN (
	         SELECT rlat.project_id, rlat.record_label_association_id rla_id, array_agg(rlat.token_index ORDER BY token_index) token
	         FROM record_label_association_token rlat
	         GROUP BY rlat.project_id, rlat.record_label_association_id
	     ) token
	     	ON rla.project_id = token.project_id AND rla.id = token.rla_id
	     INNER JOIN labeling_task_label ltl
	     	ON rla.project_id = ltl.project_id AND rla.labeling_task_label_id = ltl.id
	     INNER JOIN labeling_task lt
	     	ON ltl.project_id = lt.project_id AND lt.id = ltl.labeling_task_id	     
	     WHERE rla.return_type = '{enums.InformationSourceReturnType.YIELD.value}' --ensure extraction
	     AND rla.project_id ='{project_id}'
	 ) extract_data_grabber
	 GROUP BY record_id, project_id,source_type,is_valid_manual_label,source_id,task_id,attribute_id
)
    """


### Pandas stuff


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
