import os
import re
from typing import Any, Tuple, Dict

import pytz
import docker
import timeit
import traceback
from datetime import datetime

from graphql.error.base import GraphQLError
from submodules.model import enums, events
from submodules.model.business_objects import (
    embedder,
    embedding,
    labeling_task,
    general,
    project,
    organization,
)

from submodules.model.business_objects.embedder_payload import get
from submodules.model.business_objects.tokenization import get_doc_bin_progress
from submodules.model.models import (
    Embedder,
    EmbedderPayload,
    InformationSource,
    User,
)
from submodules.model.business_objects import record
from controller.auth.manager import get_user_by_info
from util import daemon, doc_ock, notification
from submodules.s3 import controller as s3
from controller.knowledge_base import util as knowledge_base
from util.notification import create_notification
from controller.weak_supervision import weak_supervision_service as weak_supervision

# lf container is run in frankfurt, graphql-gateway is utc --> german time zone needs to be used to match

client = docker.from_env()
__tz = pytz.timezone("Europe/Berlin")
attribute_exec_env_image = os.getenv("ATTRIBUTE_EXEC_ENV_IMAGE")
token_exec_env_image = os.getenv("TOKEN_EXEC_ENV_IMAGE")
exec_env_network = os.getenv("LF_NETWORK")


def create_payload(
    info,
    project_id: str,
    information_source_id: str,
    user_id: str,
    asynchronous: bool,
) -> EmbedderPayload:
    embedder_obj = embedder.get(project_id, information_source_id)
    count = len(embedder_obj.payloads) + 1
    general.expunge(embedder_obj)
    general.make_transient(embedder_obj)
    payload = embedder.create_payload(
        project_id=project_id,
        created_by=user_id,
        iteration=count,
        embedder_id=embedder_obj.id,
        source_code=embedder_obj.source_code,
        state=enums.PayloadState.CREATED.value,
        with_commit=True,
    )
    notification.send_organization_update(
        project_id,
        f"embedder_payload_created:{embedder_obj.id}:{payload.id}",
    )

    def prepare_and_run_execution_pipeline(
        user: User,
        payload_id: str,
        project_id: str,
        embedder_obj: Embedder,
    ) -> None:
        ctx_token = general.get_ctx_token()
        try:
            # add_file_name, input_data = prepare_input_data_for_payload(embedder_obj)
            add_file_name, input_data = "test", {}
            execution_pipeline(
                user,
                payload_id,
                project_id,
                embedder_obj,
                add_file_name,
                input_data,
            )
        except:
            general.rollback()
            print(traceback.format_exc(), flush=True)
            payload_item = get(project_id, payload_id)
            payload_item.state = enums.PayloadState.FAILED.value
            general.commit()
            create_notification(
                enums.NotificationType.EMBEDDER_FAILED,
                user_id,
                project_id,
                embedder_obj.name,
            )
        finally:
            general.reset_ctx_token(ctx_token, True)

    def prepare_input_data_for_payload(
        embedder_obj: Embedder,
    ) -> Tuple[str, Dict[str, Any]]:

        # now, collect the data
        embedding_id = __get_embedding_id_from_function(
            user_id, project_id, embedder_obj
        )
        embedding_file_name = f"embedding_tensors_{embedding_id}.csv.bz2"
        embedding_item = embedding.get(project_id, embedding_id)
        org_id = organization.get_id_by_project_id(project_id)
        if not s3.object_exists(org_id, project_id + "/" + embedding_file_name):
            notification = create_notification(
                enums.NotificationType.INFORMATION_SOURCE_S3_EMBEDDING_MISSING,
                user_id,
                project_id,
                embedding_item.name,
            )
            raise ValueError(notification.message)

        return embedding_file_name, {}

    def execution_pipeline(
        user: User,
        payload_id: str,
        project_id: str,
        embedder_item: Embedder,
        add_file_name: str,
        input_data: Dict[str, Any],
    ) -> None:

        if embedder_item.type == enums.EmbeddingType.ON_ATTRIBUTE.value:
            image = attribute_exec_env_image
        elif embedder_item.type == enums.EmbeddingType.ON_TOKEN.value:
            image = token_exec_env_image
        else:
            raise GraphQLError(f"unknown embedder type: {embedder_item.type}")

        payload_item = embedder.get_payload(project_id, payload_id)
        try:
            create_notification(
                enums.NotificationType.EMBEDDER_STARTED,
                user_id,
                project_id,
                embedder_item.name,
            )
            start = timeit.default_timer()
            run_container(
                payload_item,
                project_id,
                image,
                embedder_item.type,
                add_file_name,
                input_data,
            )
            payload_item.state = enums.PayloadState.FINISHED.value
            general.commit()
            create_notification(
                enums.NotificationType.EMBEDDER_COMPLETED,
                user_id,
                project_id,
                embedder_item.name,
            )
            notification.send_organization_update(
                project_id,
                f"embedder_payload_finished:{embedder_item.id}:{payload.id}",
            )
        except:
            general.rollback()
            print(traceback.format_exc())
            payload_item.state = enums.PayloadState.FAILED.value
            general.commit()
            create_notification(
                enums.NotificationType.EMBEDDER_FAILED,
                user_id,
                project_id,
                embedder_item.name,
            )
            notification.send_organization_update(
                project_id,
                f"embedder_payload_failed:{embedder_item.id}:{payload_item.id}",
            )
        stop = timeit.default_timer()
        general.commit()

        org_id = organization.get_id_by_project_id(project_id)
        s3.delete_object(org_id, project_id + "/" + str(payload_id))

        if payload_item.state == enums.PayloadState.FINISHED.value:
            pass

    user = get_user_by_info(info)
    if asynchronous:
        daemon.run(
            prepare_and_run_execution_pipeline,
            user,
            payload.id,
            project_id,
            embedder_obj,
        )
    else:
        prepare_and_run_execution_pipeline(
            user,
            payload.id,
            project_id,
            embedder_obj,
        )
    return payload


def run_container(
    embedder_paylod: EmbedderPayload,
    project_id: str,
    image: str,
    embedder_type: str,
    add_file_name: str,
    input_data: Dict[str, Any],
) -> None:
    project_item = project.get(project_id)
    payload_id = str(embedder_paylod.id)
    prefixed_input_name = f"{payload_id}_input"
    prefixed_function_name = f"{payload_id}_fn"
    prefixed_knowledge_base = f"{payload_id}_knowledge"
    org_id = organization.get_id_by_project_id(project_id)
    s3.put_object(
        org_id,
        project_id + "/" + prefixed_function_name,
        embedder_paylod.source_code,
    )

    if embedder_type == enums.InformationSourceType.ACTIVE_LEARNING.value:
        s3.put_object(org_id, project_id + "/" + prefixed_input_name, input_data)
        command = [
            s3.create_access_link(org_id, project_id + "/" + prefixed_input_name),
            s3.create_access_link(org_id, project_id + "/" + prefixed_function_name),
            s3.create_access_link(org_id, project_id + "/" + add_file_name),
            s3.create_file_upload_link(org_id, project_id + "/" + payload_id),
        ]
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
    container = client.containers.run(
        image=image,
        command=command,
        remove=True,
        detach=True,
        network=exec_env_network,
    )

    embedder_paylod.logs = [
        line.decode("utf-8").strip("\n")
        for line in container.logs(
            stream=True, stdout=True, stderr=True, timestamps=True
        )
    ]

    embedder_paylod.finished_at = datetime.now()
    general.commit()

    s3.delete_object(org_id, project_id + "/" + prefixed_input_name)
    s3.delete_object(org_id, project_id + "/" + prefixed_function_name)
    s3.delete_object(org_id, project_id + "/" + prefixed_knowledge_base)


# TODO: refactor this into a single function, as this is a duplicate from the lf payload scheduler
def __get_embedding_id_from_function(
    user_id: str, project_id: str, source_item: Embedder
) -> str:
    embedding_name = re.search(
        r'embedding_name\s*=\s*"([\w\W]+?)"',
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
