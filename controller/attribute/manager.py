from typing import List, Tuple
from controller.tokenization.tokenization_service import (
    request_reupload_docbins,
)
from submodules.model.business_objects import (
    attribute,
    record,
    tokenization,
    general,
    task_queue,
)
from submodules.model.models import Attribute
from submodules.model.enums import AttributeState, DataTypes
from util import daemon, notification

from controller.task_queue import manager as task_queue_manager
from submodules.model.enums import TaskType
from . import util
from sqlalchemy import sql


def get_attribute(project_id: str, attribute_id: str) -> Attribute:
    return attribute.get(project_id, attribute_id)


def get_all_attributes_by_names(
    project_id: str, attribute_names: List[str]
) -> List[Attribute]:
    return attribute.get_all_by_names(project_id, attribute_names)


def get_all_attributes(
    project_id: str, state_filter: List[str] = None
) -> List[Attribute]:
    if not state_filter:
        state_filter = [
            AttributeState.UPLOADED.value,
            AttributeState.USABLE.value,
            AttributeState.AUTOMATICALLY_CREATED.value,
        ]
    if len(state_filter) == 1 and state_filter[0].upper() == "ALL":
        state_filter = [e.value for e in AttributeState]
    return attribute.get_all_ordered(project_id, True, state_filter)


def check_composite_key(project_id: str) -> bool:
    return attribute.check_composite_key_is_valid(project_id)


def create_attribute(project_id: str, name: str) -> Attribute:
    prev_relative_position: int = attribute.get_relative_position(project_id)
    if prev_relative_position is None:
        relative_position = 1
    else:
        relative_position = prev_relative_position + 1

    attribute_item: Attribute = attribute.create(
        project_id,
        name,
        relative_position,
        with_commit=True,
    )
    return attribute_item


def create_user_attribute(project_id: str, name: str, data_type: str) -> Attribute:
    prev_relative_position: int = attribute.get_relative_position(project_id)
    if prev_relative_position is None:
        relative_position = 1
    else:
        relative_position = prev_relative_position + 1

    attribute_item: Attribute = attribute.create(
        project_id,
        name,
        relative_position,
        data_type=data_type,
        is_primary_key=False,
        user_created=True,
        state=AttributeState.INITIAL.value,
        with_commit=True,
    )
    notification.send_organization_update(
        project_id=project_id,
        message=f"calculate_attribute:created:{str(attribute_item.id)}",
    )

    return attribute_item


def update_attribute(
    project_id: str,
    attribute_id: str,
    data_type: str,
    is_primary_key: bool,
    name: str,
    source_code: str,
    visibility: str,
) -> None:
    attribute_item: Attribute = attribute.update(
        project_id,
        attribute_id,
        data_type,
        is_primary_key,
        name,
        source_code,
        with_commit=True,
        visibility=visibility,
    )

    notification.send_organization_update(
        project_id=project_id,
        message=f"calculate_attribute:updated:{str(attribute_item.id)}",
    )


def delete_attribute(project_id: str, attribute_id: str) -> None:
    attribute_item = attribute.get(project_id, attribute_id)
    if attribute_item.user_created:
        is_text_attribute = attribute_item.data_type == DataTypes.TEXT.value
        is_usable = attribute_item.state == AttributeState.USABLE.value
        if is_usable:
            record.delete_user_created_attribute(
                project_id=project_id, attribute_id=attribute_id, with_commit=True
            )
        attribute.delete(project_id, attribute_id, with_commit=True)
        if is_usable and not is_text_attribute:
            request_reupload_docbins(project_id)
        notification.send_organization_update(
            project_id=project_id, message=f"calculate_attribute:deleted:{attribute_id}"
        )
        if is_usable:
            notification.send_organization_update(
                project_id=project_id, message="attributes_updated"
            )
    else:
        raise ValueError("Attribute is not user created")


def add_running_id(
    user_id: str, project_id: str, attribute_name: str, for_retokenization: bool = True
) -> None:
    if attribute.get_by_name(project_id, attribute_name):
        raise ValueError(f"attribute with name {attribute_name} already exists")

    attribute.add_running_id(
        project_id, attribute_name, for_retokenization, with_commit=True
    )
    if for_retokenization:
        task_queue_manager.add_task(
            project_id,
            TaskType.TOKENIZATION,
            user_id,
            {
                "type": "project",
                "include_rats": True,
                "only_uploaded_attributes": False,
            },
        )


def calculate_user_attribute_all_records(
    project_id: str, user_id: str, attribute_id: str, include_rats: bool = True
) -> None:
    if attribute.get_all(
        project_id=project_id, state_filter=[AttributeState.RUNNING.value]
    ):
        __notify_attribute_calculation_failed(
            project_id=project_id,
            attribute_id=attribute_id,
            log="Calculation of attribute failed. Another attribute is already running.",
            append_to_logs=False,
        )
        return

    if tokenization.get_doc_bin_progress(project_id):
        __notify_attribute_calculation_failed(
            project_id=project_id,
            attribute_id=attribute_id,
            log="Tokenization is not finished",
            append_to_logs=False,
        )
        return

    attribute_item = attribute.get(project_id, attribute_id)
    equally_named_attributes = attribute.get_all_by_names(
        project_id, [attribute_item.name]
    )
    usable_attributes = attribute.get_all(project_id)
    if len(set(equally_named_attributes) & set(usable_attributes)) > 1:
        __notify_attribute_calculation_failed(
            project_id=project_id,
            attribute_id=attribute_id,
            log="Calculation of attribute failed. Another attribute with the same name is already in state usable or uploaded.",
            append_to_logs=False,
        )
        return
    attribute.update(
        project_id=project_id,
        attribute_id=attribute_id,
        state=AttributeState.RUNNING.value,
        with_commit=True,
        started_at=sql.func.now(),
    )
    notification.send_organization_update(
        project_id=project_id, message=f"calculate_attribute:started:{attribute_id}"
    )
    daemon.run(
        __calculate_user_attribute_all_records,
        project_id,
        user_id,
        attribute_id,
        include_rats,
    )


def __calculate_user_attribute_all_records(
    project_id: str, user_id: str, attribute_id: str, include_rats: bool
) -> None:
    session_token = general.get_ctx_token()
    try:
        calculated_attributes = util.run_attribute_calculation_exec_env(
            attribute_id=attribute_id,
            project_id=project_id,
            doc_bin="docbin_full",
        )
        if not calculated_attributes:
            __notify_attribute_calculation_failed(
                project_id=project_id,
                attribute_id=attribute_id,
                log="Calculation of attribute failed.",
            )
            return
    except Exception:
        __notify_attribute_calculation_failed(
            project_id=project_id,
            attribute_id=attribute_id,
            log="Attribute calculation failed",
        )
        general.remove_and_refresh_session(session_token)
        return

    util.add_log_to_attribute_logs(
        project_id, attribute_id, "Writing results to the database."
    )
    # add calculated attributes to database
    try:
        record.update_add_user_created_attribute(
            project_id=project_id,
            attribute_id=attribute_id,
            calculated_attributes=calculated_attributes,
            with_commit=True,
        )
    except Exception:
        record.delete_user_created_attribute(
            project_id=project_id,
            attribute_id=attribute_id,
            with_commit=True,
        )
        __notify_attribute_calculation_failed(
            project_id=project_id,
            attribute_id=attribute_id,
            log="Writing to the database failed.",
        )
        general.remove_and_refresh_session(session_token)
        return
    util.add_log_to_attribute_logs(project_id, attribute_id, "Finished writing.")

    attribute_item = attribute.get(project_id, attribute_id)
    if attribute_item.data_type == DataTypes.TEXT.value:
        util.add_log_to_attribute_logs(
            project_id, attribute_id, "Triggering tokenization."
        )
        try:
            task_queue_manager.add_task(
                project_id,
                TaskType.TOKENIZATION,
                user_id,
                {
                    "type": "attribute",
                    "attribute_id": str(attribute_item.id),
                    "include_rats": include_rats,
                },
            )

        except Exception:
            record.delete_user_created_attribute(
                project_id=project_id,
                attribute_id=attribute_id,
                with_commit=True,
            )
            __notify_attribute_calculation_failed(
                project_id=project_id,
                attribute_id=attribute_id,
                log="Writing to the database failed.",
            )
            general.remove_and_refresh_session(session_token)
            return

    else:
        util.add_log_to_attribute_logs(
            project_id, attribute_id, "Adding attribute to docbins."
        )
        request_reupload_docbins(project_id)

    attribute.update(
        project_id=project_id,
        attribute_id=attribute_id,
        state=AttributeState.USABLE.value,
        with_commit=True,
        finished_at=sql.func.now(),
    )

    notification.send_organization_update(
        project_id, f"calculate_attribute:finished:{attribute_id}"
    )
    general.remove_and_refresh_session(session_token)


def __notify_attribute_calculation_failed(
    project_id: str, attribute_id: str, log: str, append_to_logs: bool = True
) -> None:
    util.add_log_to_attribute_logs(project_id, attribute_id, log, append_to_logs)
    attribute.update(
        project_id=project_id,
        attribute_id=attribute_id,
        state=AttributeState.FAILED.value,
        with_commit=True,
    )
    notification.send_organization_update(
        project_id=project_id, message=f"calculate_attribute:error:{attribute_id}"
    )


def calculate_user_attribute_sample_records(
    project_id: str, attribute_id: str
) -> Tuple[List[str], List[str]]:
    doc_bin_samples = util.prepare_sample_records_doc_bin(
        attribute_id=attribute_id, project_id=project_id
    )
    calculated_attributes = util.run_attribute_calculation_exec_env(
        attribute_id=attribute_id, project_id=project_id, doc_bin=doc_bin_samples
    )
    return list(calculated_attributes.keys()), list(calculated_attributes.values())
