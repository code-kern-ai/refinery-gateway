from typing import Dict, Any
from controller.auth import kratos
from submodules.model import models
from submodules.model.business_objects import data_slice
from submodules.model import enums
from submodules.model.business_objects.inter_annotator import (
    check_inter_annotator_classification_records_only_used_once,
    get_current_inter_annotator_classification_users,
    get_all_inter_annotator_classification_users,
    get_classification_user_by_user_label_count,
    get_extraction_user_max_lookup,
    get_inter_annotator_extraction_users,
    get_extraction_user_by_user_label_count,
)


def resolve_inter_annotator_matrix_classification(
    labeling_task: models.LabelingTask,
    include_gold_star: bool,
    include_all_org_user: bool,
    static_slice_id: str,
):
    project_id = str(labeling_task.project_id)
    labeling_task_id = str(labeling_task.id)

    __run_checks_inter_annotator_classification(
        project_id, labeling_task_id, static_slice_id
    )

    all_users = []
    if include_all_org_user:
        users = __get_all_inter_annotator_classification_users(
            project_id, labeling_task_id, static_slice_id
        )
    else:
        users = __get_current_inter_annotator_classification_users(
            project_id, labeling_task_id, static_slice_id
        )
    if (
        not include_gold_star
        and enums.InterAnnotatorConstants.ID_GOLD_USER.value in users
    ):
        del users[enums.InterAnnotatorConstants.ID_GOLD_USER.value]
    elif (
        include_gold_star
        and enums.InterAnnotatorConstants.ID_GOLD_USER.value not in users
    ):
        users[enums.InterAnnotatorConstants.ID_GOLD_USER.value] = 0

    all_users = kratos.resolve_all_user_ids(list(users.keys()))
    all_users = [{"user": user, "count": users[user["id"]]} for user in all_users]
    all_users.sort(
        key=lambda x: (
            x["user"]["id"]
            if x["user"]["id"] != enums.InterAnnotatorConstants.ID_GOLD_USER.value
            else "zzz"
        )
    )

    elements = []
    count_lookup = __get_classification_user_by_user_label_count(
        project_id, labeling_task_id, static_slice_id
    )

    for userA in users:
        for userB in users:
            if userA == userB:
                percent = 1
            else:
                percent = count_lookup.get(userA + "@" + userB)
                if percent is None:
                    percent = -1
            elements.append(
                {"userIdA": userA, "userIdB": userB, "percent": float(percent)}
            )
    return {
        "allUsers": all_users,
        "countNames": len(all_users),
        "elements": elements,
    }


def __run_checks_inter_annotator_classification(
    project_id: str, labeling_task_id: str, slice_id: str
) -> None:
    __check_classification_records_only_used_once(
        project_id, labeling_task_id, slice_id
    )
    if slice_id:
        __check_slice_id_valid(project_id, slice_id)


def __check_slice_id_valid(project_id: str, slice_id: str) -> None:
    data_slice_item = data_slice.get(project_id, slice_id, True)
    if not data_slice_item:
        raise ValueError(f"Can't find static data slice with id {slice_id}")


def __check_classification_records_only_used_once(
    project_id: str, labeling_task_id: str, slice_id: str
) -> None:
    result = check_inter_annotator_classification_records_only_used_once(
        project_id, labeling_task_id, slice_id
    )
    if result.count > 0 and result.sum != result.count:
        raise ValueError(
            f"Project: {project_id}, task {labeling_task_id} has a missmatch in user / classification amount"
        )


def __get_current_inter_annotator_classification_users(
    project_id: str, labeling_task_id: str, slice_id: str
) -> Dict[str, int]:
    result = get_current_inter_annotator_classification_users(
        project_id, labeling_task_id, slice_id
    )
    return {x.user_id: x.distinct_records for x in result}


def __get_all_inter_annotator_classification_users(
    project_id: str, labeling_task_id: str, slice_id: str
) -> Dict[str, int]:
    result = get_all_inter_annotator_classification_users(
        project_id, labeling_task_id, slice_id
    )

    return {x.user_id: x.distinct_records for x in result}


def __get_classification_user_by_user_label_count(
    project_id: str, labeling_task_id: str, slice_id: str
) -> Dict[str, float]:
    result = get_classification_user_by_user_label_count(
        project_id, labeling_task_id, slice_id
    )

    return {x.user_lookup: x.percent for x in result}


def resolve_inter_annotator_matrix_extraction(
    labeling_task: models.LabelingTask,
    include_gold_star: bool,
    include_all_org_user: bool,
    static_slice_id: str,
):
    project_id = str(labeling_task.project_id)
    labeling_task_id = str(labeling_task.id)

    __run_checks_inter_annotator_extraction(project_id, static_slice_id)

    all_users = []
    users = __get_inter_annotator_extraction_users(
        project_id, labeling_task_id, static_slice_id, include_all_org_user
    )
    if (
        not include_gold_star
        and enums.InterAnnotatorConstants.ID_GOLD_USER.value in users
    ):
        del users[enums.InterAnnotatorConstants.ID_GOLD_USER.value]
    elif (
        include_gold_star
        and enums.InterAnnotatorConstants.ID_GOLD_USER.value not in users
    ):
        users[enums.InterAnnotatorConstants.ID_GOLD_USER.value] = 0

    all_users = kratos.resolve_all_user_ids(list(users.keys()))
    all_users = [{"user": user, "count": users[user["id"]]} for user in all_users]
    all_users.sort(
        key=lambda x: (
            x["user"]["id"]
            if x["user"]["id"] != enums.InterAnnotatorConstants.ID_GOLD_USER.value
            else "zzz"
        )
    )

    elements = []
    max_lookup = __get_extraction_user_max_lookup(
        project_id, labeling_task_id, static_slice_id
    )
    count_lookup = __get_extraction_user_by_user_label_count(
        project_id, labeling_task_id, static_slice_id
    )

    for userA in users:
        for userB in users:
            if userA == userB:
                percent = 1
            else:
                user_lookup = userA + "@" + userB
                amount = count_lookup.get(user_lookup)
                if amount is None:
                    amount = 0
                full_count = max_lookup.get(user_lookup)
                if full_count is None or full_count == 0:
                    percent = -1
                else:
                    percent = round(amount / full_count, 4)
            elements.append(
                {"user_id_a": userA, "user_id_b": userB, "percent": percent}
            )
    return {
        "allUsers": all_users,
        "countNames": len(all_users),
        "elements": elements,
    }


def __run_checks_inter_annotator_extraction(project_id: str, slice_id: str) -> None:
    if slice_id:
        __check_slice_id_valid(project_id, slice_id)


def __get_inter_annotator_extraction_users(
    project_id: str, labeling_task_id: str, slice_id: str, all_user: bool
) -> Dict[str, int]:
    result = get_inter_annotator_extraction_users(
        project_id, labeling_task_id, slice_id, all_user
    )

    return {x.user_id: x.distinct_records for x in result}


def __get_extraction_user_max_lookup(
    project_id: str, labeling_task_id: str, slice_id: str
) -> Dict[str, Any]:
    result = get_extraction_user_max_lookup(project_id, labeling_task_id, slice_id)

    return {x.user_lookup: x.possible_matches for x in result}


def __get_extraction_user_by_user_label_count(
    project_id: str, labeling_task_id: str, slice_id: str
) -> Dict[str, int]:
    result = get_extraction_user_by_user_label_count(
        project_id, labeling_task_id, slice_id
    )

    return {x.user_lookup: x.count_same for x in result}
