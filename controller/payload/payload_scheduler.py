import os
import re
from sqlalchemy.orm.attributes import flag_modified
from typing import Any, Tuple, Dict, List

import pytz
import json
import docker
import timeit
import traceback

# from datetime import datetime
from dateutil import parser
import datetime

from exceptions.exceptions import PayloadSchedulerError
from submodules.model import enums, events
from submodules.model.business_objects import (
    information_source,
    embedding,
    labeling_task,
    labeling_task_label,
    record,
    record_label_association,
    general,
    project,
    organization,
)
from submodules.model.business_objects.embedding import get_embedding_record_ids
from submodules.model.business_objects.information_source import (
    get_exclusion_record_ids,
)
from submodules.model.business_objects.labeling_task_label import (
    get_classification_labels_manual,
    get_extraction_labels_manual,
    get_label_ids_by_names,
)
from submodules.model.business_objects.payload import get_max_token, get
from submodules.model.business_objects.tokenization import (
    get_doc_bin_progress,
    get_doc_bin_table_to_json,
)
from submodules.model.models import (
    InformationSource,
    InformationSourceStatisticsExclusion,
    RecordLabelAssociation,
    InformationSourcePayload,
)
from util import daemon, doc_ock, notification
from submodules.s3 import controller as s3
from controller.knowledge_base import util as knowledge_base
from controller.misc import config_service
from util.notification import create_notification
from util.miscellaneous_functions import chunk_dict
from controller.weak_supervision import weak_supervision_service as weak_supervision
import time
import uuid

__containers_running = {}

client = docker.from_env()
__tz = pytz.timezone("Europe/Berlin")
lf_exec_env_image = os.getenv("LF_EXEC_ENV_IMAGE")
ml_exec_env_image = os.getenv("ML_EXEC_ENV_IMAGE")
exec_env_network = os.getenv("LF_NETWORK")


def create_payload(
    project_id: str,
    information_source_id: str,
    user_id: str,
    asynchronous: bool,
) -> InformationSourcePayload:
    information_source_item = information_source.get(project_id, information_source_id)
    count = len(information_source_item.payloads) + 1
    # remove session connection to prevent timeout errors, caution no update possible!
    # timeouts can occur if the data collection takes longer than the session stays active
    # TODO outsource in general file maybe
    general.expunge(information_source_item)
    general.make_transient(information_source_item)
    payload = information_source.create_payload(
        project_id=project_id,
        created_by=user_id,
        iteration=count,
        source_id=information_source_item.id,
        source_code=information_source_item.source_code,
        state=enums.PayloadState.CREATED.value,
        with_commit=True,
    )
    notification.send_organization_update(
        project_id, f"payload_created:{information_source_item.id}:{str(payload.id)}"
    )

    def prepare_and_run_execution_pipeline(
        payload_id: str,
        project_id: str,
        information_source_item: InformationSource,
        in_thread: bool = False,
    ) -> None:
        if in_thread:
            ctx_token = general.get_ctx_token()
        try:
            add_file_name, input_data = prepare_input_data_for_payload(
                information_source_item
            )
            execution_pipeline(
                payload_id,
                project_id,
                information_source_item,
                add_file_name,
                input_data,
            )
        except Exception:
            general.rollback()
            print(traceback.format_exc(), flush=True)
            payload_item = get(project_id, payload_id)
            payload_item.state = enums.PayloadState.FAILED.value
            general.commit()
            create_notification(
                enums.NotificationType.INFORMATION_SOURCE_FAILED,
                user_id,
                project_id,
                information_source_item.name,
            )
        finally:
            if in_thread:
                general.reset_ctx_token(ctx_token, True)

    def prepare_input_data_for_payload(
        information_source_item: InformationSource,
    ) -> Tuple[str, Dict[str, Any]]:
        org_id = organization.get_id_by_project_id(project_id)
        if (
            information_source_item.type
            == enums.InformationSourceType.LABELING_FUNCTION.value
        ):
            # check if docbins exist
            if not s3.object_exists(org_id, project_id + "/" + "docbin_full"):
                notification = create_notification(
                    enums.NotificationType.INFORMATION_SOURCE_S3_DOCBIN_MISSING,
                    user_id,
                    project_id,
                )
                raise ValueError(notification.message)
            return None, None

        elif (
            information_source_item.type
            == enums.InformationSourceType.ACTIVE_LEARNING.value
        ):
            # for active learning, we can not evaluate on all records that are used for training
            # as otherwise, we would retrieve a false understanding of the accuracy!
            add_information_source_statistics_exclusion(
                project_id,
                str(information_source_item.labeling_task_id),
                information_source_id,
            )

            # now, collect the data
            embedding_id = __get_embedding_id_from_function(
                user_id, project_id, information_source_item
            )
            embedding_file_name = f"embedding_tensors_{embedding_id}.csv.bz2"
            embedding_item = embedding.get(project_id, embedding_id)
            if not s3.object_exists(org_id, project_id + "/" + embedding_file_name):
                notification = create_notification(
                    enums.NotificationType.INFORMATION_SOURCE_S3_EMBEDDING_MISSING,
                    user_id,
                    project_id,
                    embedding_item.name,
                )
                raise ValueError(notification.message)
            labels_manual = None
            if (
                information_source_item.return_type
                == enums.InformationSourceReturnType.RETURN.value
            ):
                labels_manual = get_classification_labels_manual(
                    project_id, information_source_item.labeling_task_id
                )

            elif (
                information_source_item.return_type
                == enums.InformationSourceReturnType.YIELD.value
            ):
                labels_manual = get_extraction_labels_manual(
                    project_id, information_source_item.labeling_task_id
                )

            # records that are excluded for stats calculation can be used to train
            # active learning modules
            training_record_ids = get_exclusion_record_ids(information_source_id)
            input_data = json.dumps(
                {
                    "information_source_id": information_source_id,
                    "embedding_type": embedding_item.type,
                    "embedding_name": embedding_item.name,
                    "labels": {"manual": labels_manual},
                    "ids": get_embedding_record_ids(project_id),
                    "active_learning_ids": training_record_ids,
                }
            )
            return embedding_file_name, input_data

    def execution_pipeline(
        payload_id: str,
        project_id: str,
        information_source_item: InformationSource,
        add_file_name: str,
        input_data: Dict[str, Any],
    ) -> None:
        if (
            information_source_item.type
            == enums.InformationSourceType.LABELING_FUNCTION.value
        ):
            image = lf_exec_env_image
        elif (
            information_source_item.type
            == enums.InformationSourceType.ACTIVE_LEARNING.value
        ):
            image = ml_exec_env_image
        else:
            raise PayloadSchedulerError(
                f"unknown information source type: {information_source_item.type}"
            )

        payload_item = information_source.get_payload(project_id, payload_id)
        try:
            create_notification(
                enums.NotificationType.INFORMATION_SOURCE_STARTED,
                user_id,
                project_id,
                information_source_item.name,
            )
            start = timeit.default_timer()
            run_container(
                payload_item,
                project_id,
                image,
                information_source_item.type,
                add_file_name,
                input_data,
            )
            # recollect to prevent detached instance error
            payload_item = information_source.get_payload(project_id, payload_id)
            has_error = update_records(payload_item, project_id)
            if has_error:
                tmp_log_store = payload_item.logs
                berlin_now = datetime.datetime.now(__tz)
                tmp_log_store.append(
                    " ".join(
                        [
                            berlin_now.strftime("%Y-%m-%dT%H:%M:%S"),
                            "If existing, results of previous run are kept.",
                        ]
                    )
                )
                payload_item.logs = tmp_log_store
                flag_modified(payload_item, "logs")
                general.commit()
                raise ValueError(
                    "update_records resulted in errors -- see log for details"
                )

            payload_item.state = enums.PayloadState.FINISHED.value
            set_payload_progress(project_id, payload_item, 1)
            create_notification(
                enums.NotificationType.INFORMATION_SOURCE_COMPLETED,
                user_id,
                project_id,
                information_source_item.name,
            )
            notification.send_organization_update(
                project_id,
                f"payload_finished:{information_source_item.id}:{payload_id}:{information_source_item.type}",
            )
        except Exception:
            general.rollback()
            print(traceback.format_exc(), flush=True)
            payload_item.state = enums.PayloadState.FAILED.value
            general.commit()
            create_notification(
                enums.NotificationType.INFORMATION_SOURCE_FAILED,
                user_id,
                project_id,
                information_source_item.name,
            )
            notification.send_organization_update(
                project_id,
                f"payload_failed:{information_source_item.id}:{payload_item.id}:{information_source_item.type}",
            )
        stop = timeit.default_timer()
        general.commit()

        org_id = organization.get_id_by_project_id(project_id)
        s3.delete_object(org_id, project_id + "/" + str(payload_id))

        if payload_item.state == enums.PayloadState.FINISHED.value:
            try:
                weak_supervision.calculate_stats_after_source_run(
                    project_id, payload_item.source_id, user_id
                )
                notification.send_organization_update(
                    project_id,
                    f"payload_update_statistics:{information_source_item.id}:{payload_id}:{information_source_item.type}",
                )
                general.commit()
            except Exception:
                print(traceback.format_exc())

        project_item = project.get(project_id)
        doc_ock.post_event(
            user_id,
            events.AddInformationSourceRun(
                ProjectName=f"{project_item.name}-{project_item.id}",
                Type=information_source_item.type,
                Code=information_source_item.source_code,
                Logs=payload_item.logs,
                RunTime=stop - start,
            ),
        )

    if asynchronous:
        daemon.run(
            prepare_and_run_execution_pipeline,
            str(payload.id),
            project_id,
            information_source_item,
            in_thread=True,
        )
    else:
        prepare_and_run_execution_pipeline(
            str(payload.id),
            project_id,
            information_source_item,
        )
    return payload


def run_container(
    information_source_payload: InformationSourcePayload,
    project_id: str,
    image: str,
    information_source_type: str,
    add_file_name: str,
    input_data: Dict[str, Any],
) -> None:
    project_item = project.get(project_id)
    payload_id = str(information_source_payload.id)
    prefixed_input_name = f"{payload_id}_input"
    prefixed_function_name = f"{payload_id}_fn"
    prefixed_knowledge_base = f"{payload_id}_knowledge"
    org_id = organization.get_id_by_project_id(project_id)
    s3.put_object(
        org_id,
        project_id + "/" + prefixed_function_name,
        information_source_payload.source_code,
    )

    volumes = None
    if information_source_type == enums.InformationSourceType.ACTIVE_LEARNING.value:
        s3.put_object(org_id, project_id + "/" + prefixed_input_name, input_data)
        command = [
            s3.create_access_link(org_id, project_id + "/" + prefixed_input_name),
            s3.create_access_link(org_id, project_id + "/" + prefixed_function_name),
            s3.create_access_link(org_id, project_id + "/" + add_file_name),
            s3.create_file_upload_link(org_id, project_id + "/" + payload_id),
        ]
        inference_dir = get_inference_dir()
        if inference_dir:
            volumes = [f"{os.path.join(inference_dir, project_id)}:/inference"]
    else:
        s3.put_object(
            org_id,
            project_id + "/" + prefixed_knowledge_base,
            knowledge_base.build_knowledge_base_from_project(project_id),
        )
        progress = get_doc_bin_progress(project_id)
        command = [
            s3.create_access_link(org_id, project_id + "/" + "docbin_full"),
            s3.create_access_link(org_id, project_id + "/" + prefixed_function_name),
            s3.create_access_link(org_id, project_id + "/" + prefixed_knowledge_base),
            progress,
            project_item.tokenizer_blank,
            s3.create_file_upload_link(org_id, project_id + "/" + payload_id),
        ]
    information_source_payload.progress = 0.0
    general.commit()
    container_name = str(uuid.uuid4())
    container = client.containers.create(
        image=image,
        command=command,
        name=container_name,
        detach=True,
        auto_remove=True,
        network=exec_env_network,
        volumes=volumes,
    )
    set_payload_progress(project_id, information_source_payload, 0.05)
    __containers_running[container_name] = True
    daemon.run(
        read_container_logs_thread,
        project_id,
        container_name,
        payload_id,
        container,
    )
    container.start()
    # final log preparation
    information_source_payload.logs = [
        line.decode("utf-8").strip("\n")
        for line in container.logs(
            stream=True, stdout=True, stderr=True, timestamps=True
        )
        if "progress" not in line.decode("utf-8")
    ]
    del __containers_running[container_name]

    information_source_payload.finished_at = datetime.datetime.now()
    set_payload_progress(project_id, information_source_payload, 0.9)

    s3.delete_object(org_id, project_id + "/" + prefixed_input_name)
    s3.delete_object(org_id, project_id + "/" + prefixed_function_name)
    s3.delete_object(org_id, project_id + "/" + prefixed_knowledge_base)


def set_payload_progress(
    project_id: str,
    information_source_payload: InformationSourcePayload,
    progress: float,
    factor: float = 1.0,
) -> None:
    information_source_payload.progress = round(progress * factor, 4)
    general.commit()

    notification.send_organization_update(
        project_id,
        f"payload_progress:{information_source_payload.source_id}:{information_source_payload.id}:{str(information_source_payload.progress)}",
    )


def extend_logs(
    project_id: str,
    information_source_payload: InformationSourcePayload,
    logs: List[str],
) -> None:
    if not logs or len(logs) == 0:
        return

    if not information_source_payload.logs:
        information_source_payload.logs = logs
    else:
        all_logs = [log for log in information_source_payload.logs]
        all_logs += logs
        information_source_payload.logs = all_logs
    general.commit()
    # currently dummy since frontend doesn't have a log change yet
    notification.send_organization_update(
        project_id,
        f"payload_created:{information_source_payload.source_id}:{information_source_payload.id}",
    )


def read_container_logs_thread(
    project_id: str,
    name: str,
    payload_id: str,
    docker_container: Any,
):
    ctx_token = general.get_ctx_token()
    # needs to be refetched since it is not thread safe
    information_source_payload = information_source.get_payload(project_id, payload_id)
    previous_progress = -1
    last_timestamp = None
    c = 0
    while name in __containers_running:
        time.sleep(1)
        c += 1
        if c > 100:
            ctx_token = general.remove_and_refresh_session(ctx_token, True)
            information_source_payload = information_source.get_payload(
                project_id, payload_id
            )
        if name not in __containers_running:
            break
        try:
            log_lines = docker_container.logs(
                stdout=True,
                stderr=True,
                timestamps=True,
                since=last_timestamp,
            )
        except Exception:
            # failsafe for containers that shut down during the read
            break
        current_logs = [
            log
            for log in str(log_lines.decode("utf-8")).split("\n")
            if len(log.strip()) > 0
        ]

        if len(current_logs) == 0:
            continue
        last_entry = current_logs[-1]
        last_timestamp_str = last_entry.split(" ")[0]
        last_timestamp = parser.parse(last_timestamp_str).replace(
            tzinfo=None
        ) + datetime.timedelta(seconds=1)
        non_progress_logs = [log for log in current_logs if "progress" not in log]
        progress_logs = [log for log in current_logs if "progress" in log]
        if len(non_progress_logs) > 0:
            extend_logs(project_id, information_source_payload, non_progress_logs)
        if len(progress_logs) == 0:
            continue
        last_entry = float(progress_logs[-1].split("progress: ")[1].strip())
        if previous_progress == last_entry:
            continue
        previous_progress = last_entry
        set_payload_progress(
            project_id, information_source_payload, last_entry, factor=0.8
        )
    general.remove_and_refresh_session(ctx_token)


def get_inference_dir() -> str:
    if config_service.get_config_value("is_managed"):
        return os.getenv("INFERENCE_DIR")
    return None


def update_records(
    information_source_payload: InformationSourcePayload, project_id: str
) -> bool:
    org_id = organization.get_id_by_project_id(project_id)
    tmp_log_store = information_source_payload.logs

    if information_source_payload.state == enums.PayloadState.FAILED.value:
        berlin_now = datetime.datetime.now(__tz)
        tmp_log_store.append(
            " ".join(
                [
                    berlin_now.strftime("%Y-%m-%dT%H:%M:%S"),
                    "Information source task cancelled.",
                ]
            )
        )
        information_source_payload.logs = tmp_log_store
        flag_modified(information_source_payload, "logs")
        general.commit()
        return True
    try:
        output_data = json.loads(
            s3.get_object(
                org_id, str(project_id) + "/" + str(information_source_payload.id)
            )
        )
    except Exception:
        berlin_now = datetime.datetime.now(__tz)
        tmp_log_store.append(
            " ".join(
                [
                    berlin_now.strftime("%Y-%m-%dT%H:%M:%S"),
                    "Code execution exited with errors. Please check the logs.",
                ]
            )
        )
        information_source_payload.logs = tmp_log_store
        flag_modified(information_source_payload, "logs")
        general.commit()
        return True

    berlin_now = datetime.datetime.now(__tz)
    tmp_log_store.append(
        berlin_now.strftime("%Y-%m-%dT%H:%M:%S") + " Writing results to the database."
    )

    information_source: InformationSource = (
        information_source_payload.informationSource  # backref resolves in camelCase
    )
    if information_source.return_type == enums.InformationSourceReturnType.YIELD.value:
        has_errors = add_data_extraction(
            information_source_payload,
            project_id,
            information_source.labeling_task_id,
            tmp_log_store,
            output_data,
        )
    else:
        has_errors = add_data_classification(
            information_source_payload,
            project_id,
            information_source.labeling_task_id,
            tmp_log_store,
            output_data,
        )
    berlin_now = datetime.datetime.now(__tz)
    if has_errors:
        tmp_log_store.append(
            berlin_now.strftime("%Y-%m-%dT%H:%M:%S")
            + " Writing to the database failed."
        )
    else:
        tmp_log_store.append(
            berlin_now.strftime("%Y-%m-%dT%H:%M:%S") + " Finished writing."
        )
    information_source_payload.logs = tmp_log_store
    flag_modified(information_source_payload, "logs")
    general.commit()
    return has_errors


def add_data_classification(
    information_source_payload: InformationSourcePayload,
    project_id: str,
    labeling_task_id: str,
    tmp_log_store: List[str],
    output_data: Any,
) -> bool:
    record_label_associations = []
    labels_valid = {}
    labels_in_task = get_label_ids_by_names(labeling_task_id, project_id)
    my_chunks = chunk_dict(output_data)
    has_errors = False
    for chunk in my_chunks:
        valid_record_ids = record.get_ids_by_keys(chunk)
        valid_record_ids = set([x[0] for x in valid_record_ids])
        for idx, (record_id, lf_result) in enumerate(chunk.items()):
            if record_id not in valid_record_ids:
                # not an error since this is a failsaive to prevend deleted records from erroring out
                continue
            confidence, label_name = lf_result
            if __check_label_errors(
                label_name, labels_in_task, tmp_log_store, labels_valid
            ):
                has_errors = True
                continue
            if not isinstance(label_name, str):
                raise TypeError(
                    f"Expected String, but Label name is of type {type(label_name)}"
                )

            label = labeling_task_label.get_by_name(
                project_id, labeling_task_id, label_name
            )

            if label is not None:
                record_label_associations.append(
                    RecordLabelAssociation(
                        project_id=project_id,
                        record_id=record_id,
                        labeling_task_label_id=label.id,
                        source_type=enums.LabelSource.INFORMATION_SOURCE.value,
                        source_id=information_source_payload.source_id,
                        return_type=enums.InformationSourceReturnType.RETURN.value,
                        confidence=confidence,
                        created_by=information_source_payload.created_by,
                    )
                )

    record_label_association.delete_by_source_id(
        project_id, information_source_payload.source_id
    )
    if not has_errors:
        general.add_all(record_label_associations, with_commit=True)
    else:
        general.commit()
    return has_errors


def add_data_extraction(
    information_source_payload: InformationSourcePayload,
    project_id: str,
    labeling_task_id: str,
    tmp_log_store: List[str],
    output_data: Any,
) -> bool:
    record_label_associations = []
    labels_valid = {}
    labels_in_task = get_label_ids_by_names(labeling_task_id, project_id)
    has_errors = False
    my_chunks = chunk_dict(output_data)
    for chunk in my_chunks:
        max_token_num = get_max_token(chunk.keys(), labeling_task_id, project_id)
        for idx, (record_id, lf_results) in enumerate(chunk.items()):
            if record_id not in max_token_num:
                # not an error since this is a failsaive to prevend deleted records from erroring out
                continue
            for lf_result in lf_results:
                if __check_extraction_errors(
                    max_token_num,
                    record_id,
                    lf_result,
                    labels_in_task,
                    tmp_log_store,
                    labels_valid,
                ):
                    has_errors = True
                    continue
                confidence, label_name, token_idx_start, token_idx_end = lf_result

                tokens = record_label_association.create_token_objects(
                    project_id, token_idx_start, token_idx_end
                )

                label = labeling_task_label.get_by_name(
                    project_id, labeling_task_id, label_name
                )

                record_label_associations.append(
                    RecordLabelAssociation(
                        project_id=project_id,
                        record_id=record_id,
                        source_type=enums.LabelSource.INFORMATION_SOURCE.value,
                        source_id=information_source_payload.source_id,
                        labeling_task_label_id=label.id,
                        return_type=enums.InformationSourceReturnType.YIELD.value,
                        tokens=tokens,
                        confidence=confidence,
                        created_by=information_source_payload.created_by,
                    )
                )

    record_label_association.delete_by_source_id(
        project_id, information_source_payload.source_id
    )
    if not has_errors:
        general.add_all(record_label_associations, with_commit=True)
    else:
        general.commit()
    return has_errors


def __check_extraction_errors(
    max_token_num: Dict[str, int],
    record_id: str,
    lf_result,
    labels_in_task,
    tmp_log_store,
    labels_valid,
) -> bool:
    has_error = False
    confidence, label_name, token_idx_start, token_idx_end = lf_result
    max_token = max_token_num[record_id]
    if token_idx_start > max_token:
        berlin_now = datetime.datetime.now(__tz)
        tmp_log_store.append(
            berlin_now.strftime("%Y-%m-%dT%H:%M:%S")
            + f" token start {{{token_idx_start}}} exceeds record {{{record_id}}} max token {{{max_token}}}"
        )
        has_error = True
    if token_idx_end > max_token:
        berlin_now = datetime.datetime.now(__tz)
        tmp_log_store.append(
            berlin_now.strftime("%Y-%m-%dT%H:%M:%S")
            + f" token end {{{token_idx_end}}} exceeds record {{{record_id}}} max token {{{max_token}}}"
        )
        has_error = True
    if token_idx_end - token_idx_start < 1:
        berlin_now = datetime.datetime.now(__tz)
        tmp_log_store.append(
            berlin_now.strftime("%Y-%m-%dT%H:%M:%S")
            + f" token span without length detected. start {{{token_idx_start}}}, end {{{token_idx_end}}} -> length {token_idx_start - token_idx_end} record {{{record_id}}}"
        )
        has_error = True

    return has_error or __check_label_errors(
        label_name, labels_in_task, tmp_log_store, labels_valid
    )


def __check_label_errors(
    label_name: str,
    labels_in_task: List[str],
    tmp_log_store: List[Any],
    labels_valid: Dict[str, bool],
) -> bool:
    if label_name not in labels_valid:
        if label_name not in labels_in_task:
            berlin_now = datetime.datetime.now(__tz)
            tmp_log_store.append(
                berlin_now.strftime("%Y-%m-%dT%H:%M:%S")
                + f" Provided label {{{label_name}}} couldn't be found for this task"
            )
            labels_valid[label_name] = False
        else:
            labels_valid[label_name] = True
    return not labels_valid[label_name]


def __get_embedding_id_from_function(
    user_id: str, project_id: str, source_item: InformationSource
) -> str:
    embedding_name = re.search(
        r'embedding_name\s*=\s*"([\w\W]+?)"',
        source_item.source_code,
        re.IGNORECASE,
    )
    if not embedding_name:
        # newer bricks modules
        embedding_name = re.search(
            r'EMBEDDING: str = "([\w\W]+?)"',
            source_item.source_code,
            re.IGNORECASE,
        )
    if not embedding_name:
        # older bricks modules
        embedding_name = re.search(
            r'YOUR_EMBEDDING: str = "([\w\W]+?)"',
            source_item.source_code,
            re.IGNORECASE,
        )
    if not embedding_name:
        raise ValueError("Can't extract embedding from function code")
    embedding_name = embedding_name.group(1)

    embedding_item = embedding.get_embedding_id_and_type(project_id, embedding_name)
    task_item = labeling_task.get(project_id, source_item.labeling_task_id)

    if (
        not embedding_item
        or (
            embedding_item.type == enums.EmbeddingType.ON_ATTRIBUTE.value
            and task_item.task_type
            == enums.LabelingTaskType.INFORMATION_EXTRACTION.value
        )
        or (
            embedding_item.type == enums.EmbeddingType.ON_TOKEN.value
            and task_item.task_type == enums.LabelingTaskType.CLASSIFICATION.value
        )
    ):
        notification_item = create_notification(
            enums.NotificationType.INFORMATION_SOURCE_CANT_FIND_EMBEDDING,
            user_id,
            project_id,
            embedding_name,
            task_item.name,
        )
        raise ValueError(notification_item.message)

    return str(embedding_item.id)


def add_information_source_statistics_exclusion(
    project_id: str, labeling_task_id: str, information_source_id: str
) -> None:
    information_source.delete_sources_exlusion_entries(
        project_id, information_source_id, with_commit=True
    )
    exclusions = [
        InformationSourceStatisticsExclusion(
            record_id=row.record_id,
            source_id=information_source_id,
            project_id=project_id,
        )
        for idx, row in enumerate(
            record_label_association.get_manual_records(project_id, labeling_task_id)
        )
        if idx % 2 == 0
    ]
    general.add_all(exclusions, with_commit=True)


def prepare_sample_records_doc_bin(
    project_id: str, information_source_id: str
) -> Tuple[str, List[str]]:
    sample_records = record.get_attribute_calculation_sample_records(project_id)

    sample_records_doc_bin = get_doc_bin_table_to_json(
        project_id=project_id,
        missing_columns=record.get_missing_columns_str(project_id),
        record_ids=[r[0] for r in sample_records],
    )
    project_item = project.get(project_id)
    org_id = str(project_item.organization_id)
    prefixed_doc_bin = f"{information_source_id}_doc_bin.json"
    s3.put_object(
        org_id,
        project_id + "/" + prefixed_doc_bin,
        sample_records_doc_bin,
    )

    return prefixed_doc_bin, sample_records


def run_labeling_function_exec_env(
    project_id: str, information_source_id: str, prefixed_doc_bin: str
) -> Tuple[List[str], List[List[str]], bool]:
    information_source_item = information_source.get(project_id, information_source_id)

    prefixed_function_name = f"{information_source_id}_fn"
    prefixed_payload = f"{information_source_id}_payload.json"
    prefixed_knowledge_base = f"{information_source_id}_knowledge"
    project_item = project.get(project_id)
    org_id = str(project_item.organization_id)

    s3.put_object(
        org_id,
        project_id + "/" + prefixed_function_name,
        information_source_item.source_code,
    )

    s3.put_object(
        org_id,
        project_id + "/" + prefixed_knowledge_base,
        knowledge_base.build_knowledge_base_from_project(project_id),
    )

    tokenization_progress = get_doc_bin_progress(project_id)

    command = [
        s3.create_access_link(org_id, project_id + "/" + prefixed_doc_bin),
        s3.create_access_link(org_id, project_id + "/" + prefixed_function_name),
        s3.create_access_link(org_id, project_id + "/" + prefixed_knowledge_base),
        tokenization_progress,
        project_item.tokenizer_blank,
        s3.create_file_upload_link(org_id, project_id + "/" + prefixed_payload),
    ]

    container = client.containers.run(
        image=lf_exec_env_image,
        command=command,
        remove=True,
        detach=True,
        network=exec_env_network,
    )

    container_logs = [
        line.decode("utf-8").strip("\n")
        for line in container.logs(
            stream=True, stdout=True, stderr=True, timestamps=True
        )
    ]

    code_has_errors = False

    try:
        payload = s3.get_object(org_id, project_id + "/" + prefixed_payload)
        calculated_labels = json.loads(payload)
    except Exception:
        print("Could not grab data from s3 -- labeling function")
        code_has_errors = True
        calculated_labels = {}

    if not prefixed_doc_bin == "docbin_full":
        # sample records docbin should be deleted after calculation
        s3.delete_object(org_id, project_id + "/" + prefixed_doc_bin)
    s3.delete_object(org_id, project_id + "/" + prefixed_function_name)
    s3.delete_object(org_id, project_id + "/" + prefixed_payload)
    s3.delete_object(org_id, project_id + "/" + prefixed_knowledge_base)

    return calculated_labels, container_logs, code_has_errors
