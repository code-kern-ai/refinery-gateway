import ast
import json
import logging
import time
import re
from typing import Dict, Any, List, Optional

from submodules.model import enums, UploadTask, Project
from submodules.model.business_objects import (
    organization,
    project,
    attribute,
    labeling_task,
    data_slice,
    labeling_task_label,
    general,
    embedding,
    record_label_association,
    information_source,
    knowledge_base,
    record,
    user,
    knowledge_term,
    weak_supervision,
    task_queue,
    upload_task,
    comments as comment,
)
from submodules.model.enums import NotificationType
from controller.labeling_access_link import manager as link_manager
from util import notification, file, security
from submodules.model import daemon
from util.decorator import param_throttle
from controller.embedding import manager as embedding_manager
from util.notification import create_notification
from submodules.s3 import controller as s3
import os
from sqlalchemy import sql

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def import_file_by_task(project_id: str, task: UploadTask) -> None:
    ensure_project_exists(project_id)
    logger.info(f"Started import of project {project_id}")
    org_id = organization.get_id_by_project_id(project_id)
    task.state = enums.UploadStates.IN_PROGRESS.value
    notification.send_organization_update(
        project_id, f"file_upload:{str(task.id)}:state:{task.state}", is_global=True
    )
    is_zip = task.file_name[-4:] == ".zip"
    if is_zip:
        file_name = s3.download_object(
            org_id, project_id + "/" + f"{task.id}/{task.file_name}", "zip"
        )
        key = security.decrypt(task.key)
        data = file.zip_to_json(file_name, key)
        upload_task.remove_key(project_id, task.id, with_commit=True)
        if os.path.exists(file_name):
            os.remove(file_name)
    else:
        data = json.loads(
            s3.get_object(org_id, project_id + "/" + f"{task.id}/{task.file_name}")
        )
    import_file(project_id, task.user_id, data, str(task.id))
    task.state = enums.UploadStates.DONE.value
    task.progress = 100
    general.commit()


def ensure_project_exists(project_id: str) -> None:
    # wait for porject existance on db
    project_item = project.get(project_id)
    count = 0
    while not project_item:
        time.sleep(1)
        project_item = project.get(project_id)
        count += 1
        if count > 10:
            raise ValueError(f"Project with id:{project_id} cant be found on db")


def import_sample_project(
    user_id: str, organization_id: str, project_name: str, project_type: str
) -> Project:
    if project_type == enums.SampleProjectType.CLICKBAIT_INITIAL.value:
        file_name = "sample_projects/clickbait_initial.zip"
    elif project_type == enums.SampleProjectType.CLICKBAIT.value:
        file_name = "sample_projects/clickbait.zip"
    elif project_type == enums.SampleProjectType.AG_NEWS_INITIAL.value:
        file_name = "sample_projects/ag_news_initial.zip"
    elif project_type == enums.SampleProjectType.AG_NEWS.value:
        file_name = "sample_projects/ag_news.zip"
    elif project_type == enums.SampleProjectType.CONVERSATIONAL_AI_INITIAL.value:
        file_name = "sample_projects/conversational_ai_initial.zip"
    elif project_type == enums.SampleProjectType.CONVERSATIONAL_AI.value:
        file_name = "sample_projects/conversational_ai.zip"
    elif project_type == enums.SampleProjectType.DEV_GLOBAL_GUARD_QUESTIONS.value:
        file_name = "sample_projects/DEV_global_guard_questions.zip"
    elif project_type == enums.SampleProjectType.DEV_GLOBAL_GUARD_REFERENCES.value:
        file_name = "sample_projects/DEV_global_guard_references.zip"
    else:
        raise Exception("Unknown sample project" + project_type)
    if not project_name:
        project_name = "Sample Project"
    if os.path.exists(file_name):
        project_description = (
            "Once the project has been initialized, you'll be redirected into it."
        )
        project_item = project.create(
            organization_id,
            project_name,
            project_description,
            user_id,
            status=enums.ProjectStatus.INIT_SAMPLE_PROJECT,
        )
        create_notification(
            NotificationType.IMPORT_SAMPLE_PROJECT,
            user_id,
            project_item.id,
        )
        notification.send_organization_update(
            project_item.id, f"project_update:{str(project_item.id)}", is_global=True
        )
        data = file.zip_to_json(file_name)
        import_file(project_item.id, user_id, data)
        project_item = project.update(project_item.id, name=project_name)

        general.commit()

        record_label_association.update_user_id_for_sample_project(
            str(project_item.id), user_id, True
        )

        notification.send_organization_update(
            project_item.id, f"project_update:{str(project_item.id)}", is_global=True
        )
        return project_item


def import_file(
    project_id: str,
    import_user_id: str,
    data: Dict[str, Dict[str, Any]],
    task_id: Optional[str] = None,
) -> None:
    """Imports data for a project. Loads a file form s3-storage into
    JSON format, extracts data and writes it to according database tables.
    Dictionaries are used to match old ids to new ids for linking entities
    according to the old project. Please take note that this handler
    may needs regular refactoring in case of database model changes.
    """
    send_progress_update_throttle(project_id, task_id, 0)
    project_item = project.get(project_id)
    if not project_item.name:
        project_item.name = data.get(
            "project_details_data",
        ).get(
            "name",
        )
    project_item.description = data.get(
        "project_details_data",
    ).get(
        "description",
    )
    project_item.tokenizer = data.get(
        "project_details_data",
    ).get(
        "tokenizer",
    )
    spacy_language = data.get(
        "project_details_data",
    ).get(
        "tokenizer",
    )[:2]
    project_item.tokenizer_blank = spacy_language
    project_item.status = data.get(
        "project_details_data",
    ).get(
        "status",
    )
    old_project_id = data.get(
        "project_details_data",
    ).get("id")
    project_id_by_old_id = {}
    if old_project_id:
        project_id_by_old_id[
            data.get(
                "project_details_data",
            ).get("id")
        ] = project_id

    send_progress_update_throttle(project_id, task_id, 10)

    attribute_ids_by_old_id = {}
    attribute_ids_by_old_name = {}
    for attribute_item in data.get(
        "attributes_data",
    ):
        attribute_object = attribute.create(
            name=attribute_item.get(
                "name",
            ),
            data_type=attribute_item.get(
                "data_type",
            ),
            is_primary_key=attribute_item.get(
                "is_primary_key",
            ),
            relative_position=attribute_item.get(
                "relative_position",
            ),
            user_created=attribute_item.get(
                "user_created",
            ),
            state=attribute_item.get(
                "state",
            ),
            logs=attribute_item.get(
                "logs",
            ),
            source_code=attribute_item.get(
                "source_code",
            ),
            visibility=attribute_item.get("visibility"),
            started_at=attribute_item.get("started_at"),
            finished_at=attribute_item.get("finished_at"),
            project_id=project_id,
        )
        attribute_ids_by_old_id[
            attribute_item.get(
                "id",
            )
        ] = attribute_object.id
        attribute_ids_by_old_name[
            attribute_item.get(
                "name",
            )
        ] = attribute_object.id
    send_progress_update_throttle(project_id, task_id, 20)

    labeling_task_ids = {}
    for labeling_task_item in data.get(
        "labeling_tasks_data",
    ):
        task_object = labeling_task.create(
            attribute_id=attribute_ids_by_old_id.get(
                labeling_task_item.get(
                    "attribute_id",
                )
            ),
            name=labeling_task_item.get(
                "name",
            ),
            task_target=labeling_task_item.get(
                "task_target",
            ),
            task_type=labeling_task_item.get(
                "task_type",
            ),
            project_id=project_id,
        )
        labeling_task_ids[
            labeling_task_item.get(
                "id",
            )
        ] = task_object.id

    labeling_task_labels_ids = {}
    for label_item in data.get(
        "labeling_task_labels_data",
    ):
        label_object = labeling_task_label.create(
            project_id=project_id,
            name=label_item.get(
                "name",
            ),
            labeling_task_id=labeling_task_ids.get(
                label_item.get(
                    "labeling_task_id",
                )
            ),
            label_color=label_item.get("color"),
            label_hotkey=label_item.get("hotkey"),
        )
        labeling_task_labels_ids[
            label_item.get(
                "id",
            )
        ] = label_object.id

    send_progress_update_throttle(project_id, task_id, 30)

    record_ids = {}
    for record_item in data.get(
        "records_data",
    ):
        record_object = record.create(
            record_data=record_item.get(
                "data",
            ),
            category=record_item.get(
                "category",
            ),
            project_id=project_id,
        )
        record_ids[
            record_item.get(
                "id",
            )
        ] = record_object.id

    for record_attribute_token_statistics_item in data.get(
        "record_attribute_token_statistics_data",
    ):
        record.create_record_attribute_token_statistics(
            project_id=project_id,
            record_id=record_ids.get(
                record_attribute_token_statistics_item.get(
                    "record_id",
                )
            ),
            attribute_id=attribute_ids_by_old_id.get(
                record_attribute_token_statistics_item.get(
                    "attribute_id",
                )
            ),
            num_token=record_attribute_token_statistics_item.get(
                "num_token",
            ),
        )

    send_progress_update_throttle(project_id, task_id, 40)

    def __transform_embedding_by_name(embedding_name: str):
        splitted_name = embedding_name.split("-")
        attribute_name = splitted_name[0]
        embedding_type = splitted_name[1]
        model = "-".join(splitted_name[2:])
        if "bag-of-words" == model or "bag-of-characters" == model or "tf-idf" == model:
            platform = enums.EmbeddingPlatform.PYTHON.value
        else:
            platform = enums.EmbeddingPlatform.HUGGINGFACE.value
        name = f"{attribute_name}-{embedding_type}-{platform}-{model}"
        return platform, model, name

    embedding_ids = {}
    embedding_name_mapping = {}
    if data.get(
        "embeddings_data",
    ):
        # if tensor data exists use that otherwise recreate embedding
        for embedding_item in data.get(
            "embeddings_data",
        ):
            if not embedding_item.get("platform"):
                platform, model, name = __transform_embedding_by_name(
                    embedding_item.get("name")
                )
                embedding_item["platform"] = platform
                embedding_item["model"] = model
                embedding_name_mapping[embedding_item.get("name")] = name
                embedding_item["name"] = name

            attribute_id = embedding_item.get("attribute_id")
            embedding_name = embedding_item.get("name")
            if attribute_id:
                attribute_id = attribute_ids_by_old_id.get(attribute_id)
            else:
                attribute_name = __get_attribute_name_from_embedding_name(
                    embedding_name
                )
                attribute_id = attribute_ids_by_old_name[attribute_name]

            finished_at_str = "finished_at" in embedding_item
            if not finished_at_str:
                embedding_item["finished_at"] = sql.func.now()

            embedding_object = embedding.create(
                project_id=project_id,
                attribute_id=attribute_id,
                name=embedding_name,
                state="FINISHED",
                created_by=import_user_id,
                custom=embedding_item.get(
                    "custom",
                ),
                type=embedding_item.get(
                    "type",
                ),
                started_at=embedding_item.get(
                    "started_at",
                ),
                finished_at=embedding_item.get(
                    "finished_at",
                ),
                platform=embedding_item.get(
                    "platform",
                ),
                model=embedding_item.get(
                    "model",
                ),
                filter_attributes=embedding_item.get("filter_attributes"),
                additional_data=embedding_item.get(
                    "additional_data",
                ),
            )
            embedding_ids[
                embedding_item.get(
                    "id",
                )
            ] = embedding_object.id
        if data.get(
            "embedding_tensors_data",
        ):
            for embedding_tensor_item in data.get(
                "embedding_tensors_data",
            ):
                embedding.create_tensor(
                    project_id=project_id,
                    record_id=record_ids.get(
                        embedding_tensor_item.get(
                            "record_id",
                        )
                    ),
                    embedding_id=embedding_ids.get(
                        embedding_tensor_item.get(
                            "embedding_id",
                        )
                    ),
                    data=embedding_tensor_item.get(
                        "data",
                    ),
                    sub_key=embedding_tensor_item.get(
                        "sub_key",
                    ),
                )

    def __replace_embedding_name(
        source_code: str, embedding_name_mapping: Dict[str, str]
    ) -> str:
        code = source_code
        for embedding_name in embedding_name_mapping.keys():
            double_quoted_name = f'"{embedding_name}"'
            single_quoted_name = f"'{embedding_name}'"
            if double_quoted_name in code:
                code = code.replace(
                    double_quoted_name, f'"{embedding_name_mapping[embedding_name]}"'
                )
            if single_quoted_name in source_code:
                code = code.replace(
                    single_quoted_name, f"'{embedding_name_mapping[embedding_name]}'"
                )
        return code

    information_source_ids = {}
    for information_source_item in data.get(
        "information_sources_data",
    ):
        if embedding_name_mapping:
            information_source_item["source_code"] = __replace_embedding_name(
                information_source_item.get(
                    "source_code",
                ),
                embedding_name_mapping,
            )
        information_source_object = information_source.create(
            name=information_source_item.get(
                "name",
            ),
            type=information_source_item.get(
                "type",
            ),
            return_type=information_source_item.get(
                "return_type",
            ),
            description=information_source_item.get(
                "description",
            ),
            source_code=information_source_item.get(
                "source_code",
            ),
            is_selected=information_source_item.get(
                "is_selected",
            ),
            version=information_source_item.get(
                "version",
            ),
            labeling_task_id=labeling_task_ids.get(
                information_source_item.get(
                    "labeling_task_id",
                )
            ),
            created_at=information_source_item.get(
                "created_at",
            ),
            project_id=project_id,
            with_commit=False,
        )
        information_source_ids[
            information_source_item.get(
                "id",
            )
        ] = information_source_object.id

    send_progress_update_throttle(project_id, task_id, 50)

    # add non existing user
    used_user_ids = []
    for data_slice_item in data.get(
        "data_slice_data",
    ):
        created_by = data_slice_item.get(
            "created_by",
        )
        if created_by not in used_user_ids:
            used_user_ids.append(created_by)

    for record_label_association_item in data.get(
        "record_label_associations_data",
    ):
        created_by = record_label_association_item.get(
            "created_by",
        )
        if created_by not in used_user_ids:
            used_user_ids.append(created_by)

    if data.get("weak_supervision_task_data"):
        for weak_supervision_item in data.get("weak_supervision_task_data"):
            created_by = weak_supervision_item.get("created_by")
            if created_by not in used_user_ids:
                used_user_ids.append(created_by)

    if "comments" in data:
        for comment_item in data.get("comments"):
            created_by = comment_item.get("created_by")
            if created_by not in used_user_ids:
                used_user_ids.append(created_by)

    if used_user_ids:
        existing_users = user.get_by_id_list(used_user_ids)
        existing_users = [str(u.id) for u in existing_users]
        for user_id in used_user_ids:
            if user_id and user_id not in existing_users:
                # currently without organization to know they are imported/dummy -- maybe there is a better solution?
                user.create(user_id=user_id)

    data_slice_ids = {}
    if data.get(
        "data_slice_data",
    ):
        for data_slice_item in data.get(
            "data_slice_data",
        ):
            data_slice_object = data_slice.create(
                name=data_slice_item.get(
                    "name",
                ),
                filter_data=ast.literal_eval(
                    replace_by_mappings(
                        str(
                            data_slice_item.get(
                                "filter_data",
                            )
                        ),
                        mappings=[
                            attribute_ids_by_old_id,
                            labeling_task_ids,
                            labeling_task_labels_ids,
                            information_source_ids,
                            record_ids,
                        ],
                    )
                ),
                count_sql=replace_by_mappings(
                    str(
                        data_slice_item.get(
                            "count_sql",
                        )
                    ),
                    mappings=[
                        project_id_by_old_id,
                        attribute_ids_by_old_id,
                        labeling_task_ids,
                        labeling_task_labels_ids,
                        information_source_ids,
                        record_ids,
                    ],
                ),
                filter_raw=ast.literal_eval(
                    replace_by_mappings(
                        str(
                            data_slice_item.get(
                                "filter_raw",
                            )
                        ),
                        mappings=[
                            attribute_ids_by_old_id,
                            labeling_task_ids,
                            labeling_task_labels_ids,
                            information_source_ids,
                            record_ids,
                        ],
                    )
                ),
                static=data_slice_item.get(
                    "static",
                ),
                count=data_slice_item.get(
                    "count",
                ),
                created_at=data_slice_item.get(
                    "created_at",
                ),
                created_by=data_slice_item.get(
                    "created_by",
                ),
                slice_type=data_slice_item.get(
                    "slice_type",
                ),
                info=data_slice_item.get(
                    "info",
                ),
                project_id=project_id,
            )
            data_slice_ids[
                data_slice_item.get(
                    "id",
                )
            ] = data_slice_object.id
            if data_slice_object.slice_type == enums.SliceTypes.STATIC_DEFAULT.value:
                link_manager.generate_data_slice_access_link(
                    project_id, import_user_id, data_slice_object.id, with_commit=False
                )

    for information_source_payload_item in data.get(
        "information_source_payloads_data",
    ):
        information_source.create_payload(
            source_id=information_source_ids.get(
                information_source_payload_item.get(
                    "source_id",
                )
            ),
            state=information_source_payload_item.get(
                "state",
            ),
            created_at=information_source_payload_item.get(
                "created_at",
            ),
            finished_at=information_source_payload_item.get(
                "finished_at",
            ),
            iteration=information_source_payload_item.get(
                "iteration",
            ),
            source_code=information_source_payload_item.get(
                "source_code",
            ),
            logs=information_source_payload_item.get(
                "logs",
            ),
            project_id=project_id,
        )

    send_progress_update_throttle(project_id, task_id, 60)
    for information_source_statistics_item in data.get(
        "information_source_statistics_data",
    ):
        information_source.create_statistics(
            source_id=information_source_ids.get(
                information_source_statistics_item.get(
                    "source_id",
                )
            ),
            labeling_task_label_id=labeling_task_labels_ids.get(
                information_source_statistics_item.get(
                    "labeling_task_label_id",
                )
            ),
            project_id=project_id,
            true_positives=information_source_statistics_item.get(
                "true_positives",
            ),
            false_positives=information_source_statistics_item.get(
                "false_positives",
            ),
            false_negatives=information_source_statistics_item.get(
                "false_negatives",
            ),
            record_coverage=information_source_statistics_item.get(
                "record_coverage",
            ),
            total_hits=information_source_statistics_item.get(
                "total_hits",
            ),
            source_conflicts=information_source_statistics_item.get(
                "source_conflicts",
            ),
            source_overlaps=information_source_statistics_item.get(
                "source_overlaps",
            ),
        )

    send_progress_update_throttle(project_id, task_id, 70)
    if data.get(
        "data_slice_record_association_data",
    ):
        for data_slice_record_association_item in data.get(
            "data_slice_record_association_data",
        ):
            data_slice.create_association(
                data_slice_id=data_slice_ids.get(
                    data_slice_record_association_item.get(
                        "data_slice_id",
                    )
                ),
                record_id=record_ids.get(
                    data_slice_record_association_item.get(
                        "record_id",
                    )
                ),
                project_id=project_id,
                outlier_score=data_slice_record_association_item.get(
                    "outlier_score",
                ),
            )

    weak_supervision_ids = {}
    if data.get("weak_supervision_task_data"):
        for weak_supervision_item in data.get("weak_supervision_task_data"):
            weak_supervision_task = weak_supervision.create_task(
                project_id=project_id,
                state=weak_supervision_item.get("state"),
                created_at=weak_supervision_item.get("created_at"),
                created_by=weak_supervision_item.get("created_by"),
                finished_at=weak_supervision_item.get("finished_at"),
                selected_information_sources=weak_supervision_item.get(
                    "selected_information_sources"
                ),
                selected_labeling_tasks=weak_supervision_item.get(
                    "selected_labeling_tasks"
                ),
                distinct_records=weak_supervision_item.get("distinct_records"),
                result_count=weak_supervision_item.get("result_count"),
            )
            weak_supervision_ids[weak_supervision_item.get("id")] = (
                weak_supervision_task.id
            )

    send_progress_update_throttle(project_id, task_id, 80)

    # add rlas
    record_label_association_ids = {}
    for record_label_association_item in data.get(
        "record_label_associations_data",
    ):
        association = record_label_association.create(
            project_id=project_id,
            record_id=record_ids.get(
                record_label_association_item.get(
                    "record_id",
                )
            ),
            labeling_task_label_id=labeling_task_labels_ids.get(
                record_label_association_item.get("labeling_task_label_id")
            ),
            created_by=record_label_association_item.get(
                "created_by",
            ),
            source_type=record_label_association_item.get(
                "source_type",
            ),
            return_type=record_label_association_item.get(
                "return_type",
            ),
            is_gold_star=record_label_association_item.get(
                "is_gold_star",
            ),
            source_id=information_source_ids.get(
                record_label_association_item.get(
                    "source_id",
                )
            ),
            confidence=record_label_association_item.get(
                "confidence",
            ),
            created_at=record_label_association_item.get(
                "created_at",
            ),
            weak_supervision_id=weak_supervision_ids.get(
                record_label_association_item.get("weak_supervision_id")
            ),
            is_valid_manual_label=record_label_association_item.get(
                "is_valid_manual_label"
            ),
        )

        record_label_association_ids[
            record_label_association_item.get(
                "id",
            )
        ] = association.id

    send_progress_update_throttle(project_id, task_id, 90)
    for token_item in data.get(
        "record_label_association_tokens_data",
    ):
        record_label_association.import_token_object(
            project_id=project_id,
            record_label_association_id=record_label_association_ids.get(
                token_item.get(
                    "record_label_association_id",
                )
            ),
            token_index=token_item.get(
                "token_index",
            ),
            is_beginning_token=token_item.get(
                "is_beginning_token",
            ),
        )

    send_progress_update_throttle(project_id, task_id, 99)
    knowledge_base_ids = {}
    for knowledge_base_item in data.get(
        "knowledge_bases_data",
    ):
        knowledge_base_object = knowledge_base.create(
            project_id=project_id,
            name=knowledge_base_item.get(
                "name",
            ),
            description=knowledge_base_item.get(
                "description",
            ),
        )
        knowledge_base_ids[
            knowledge_base_item.get(
                "id",
            )
        ] = knowledge_base_object.id

    for term_item in data.get(
        "terms_data",
    ):
        knowledge_term.create(
            project_id=project_id,
            knowledge_base_id=knowledge_base_ids.get(
                term_item.get(
                    "knowledge_base_id",
                )
            ),
            value=term_item.get(
                "value",
            ),
            comment=term_item.get(
                "comment",
            ),
            blacklisted=term_item.get(
                "blacklisted",
            ),
        )
    comment_data = data.get("comments")
    if comment_data:
        for comment_item in comment_data:
            old_xfkey = comment_item.get("xfkey")
            new_xfkey = None
            xftype = comment_item.get("xftype")
            if xftype == enums.CommentCategory.RECORD.value:
                new_xfkey = record_ids.get(old_xfkey)
            elif xftype == enums.CommentCategory.LABELING_TASK.value:
                new_xfkey = labeling_task_ids.get(old_xfkey)
            elif xftype == enums.CommentCategory.ATTRIBUTE.value:
                new_xfkey = attribute_ids_by_old_id.get(old_xfkey)
            elif xftype == enums.CommentCategory.LABEL.value:
                new_xfkey = labeling_task_labels_ids.get(old_xfkey)
            elif xftype == enums.CommentCategory.DATA_SLICE.value:
                new_xfkey = data_slice_ids.get(old_xfkey)
            elif xftype == enums.CommentCategory.EMBEDDING.value:
                new_xfkey = embedding_ids.get(old_xfkey)
            elif xftype == enums.CommentCategory.HEURISTIC.value:
                new_xfkey = information_source_ids.get(old_xfkey)
            elif xftype == enums.CommentCategory.KNOWLEDGE_BASE.value:
                new_xfkey = knowledge_base_ids.get(old_xfkey)
            if not new_xfkey:
                continue

            comment.create(
                xfkey=new_xfkey,
                xftype=comment_item.get("xftype"),
                comment=comment_item.get("comment"),
                created_by=comment_item.get("created_by"),
                project_id=project_id,
                order_key=comment_item.get("order_key"),
                is_markdown=comment_item.get("is_markdown"),
                created_at=comment_item.get("created_at"),
                is_private=comment_item.get("is_private"),
            )

    general.commit()
    daemon.run_without_db_token(
        __post_processing_import_threaded,
        project_id,
        task_id,
        embedding_ids,
        data,
        import_user_id,
    )
    send_progress_update(project_id, task_id, 100)
    logger.info(f"Finished import of project {project_id}")


def __post_processing_import_threaded(
    project_id: str,
    task_id: str,
    embedding_ids: List[str],
    data: Dict[str, Any],
    user_id: str,
) -> None:
    time.sleep(5)
    ctx_token = general.get_ctx_token()
    c = 1
    while True:
        c += 1
        if c > 12:
            ctx_token = general.remove_and_refresh_session(ctx_token, True)
            c = 1
        if task_queue.get_by_tokenization(project_id):
            logger.info(f"Waiting for tokenization of project {project_id}")
            time.sleep(5)
        else:
            logger.info(
                f"Tokenization finished, continue with embedding handling of project {project_id}"
            )
            break
    if not data.get(
        "embedding_tensors_data",
    ):
        embedding_manager.recreate_embeddings(project_id, user_id=user_id)
    else:
        for old_id in embedding_ids:
            embedding_manager.request_tensor_upload(
                project_id, str(embedding_ids[old_id])
            )
    general.remove_and_refresh_session(ctx_token)


def get_project_export_dump(
    project_id: str, user_id: str, export_options: Dict[str, bool]
) -> str:
    """Exports data of a project in JSON-String format. Queries all useful database entries and
    puts them in a format which again fits for import. For some entities database joins
    are useful, so there are vanilla SQL statements in execute-blocks.
    Please take note that this handler may needs regular refactoring in case of database model changes.
    """

    logger.info(f"Started export of project {project_id}")
    # -------------------------- PREPARE OPTIONS -----------------------------
    project_item = project.get(project_id)
    attributes = []
    labeling_tasks = []
    labeling_task_labels = []
    data_slices = []
    data_slice_record_association = []
    records = []
    record_attribute_token_statistics = []
    embeddings = []
    embedding_tensors = []
    information_sources = []
    information_source_statistics = []
    information_source_payloads = []
    record_label_associations = []
    record_label_association_tokens = []
    knowledge_bases = []
    weak_supervision_task = []
    terms = []
    comments = []
    # -------------------- READ OF ENTITIES BY SQLALCHEMY --------------------

    if "basic project data" in export_options:
        attributes = attribute.get_all(project_id, state_filter=[])
        labeling_tasks = labeling_task.get_all(project_id)
        labeling_task_labels = labeling_task_label.get_all(project_id)
        data_slices = data_slice.get_all(project_id)
        data_slice_record_association = data_slice.get_all_associations(project_id)

    if "records" in export_options:
        records = record.get_all(project_id)
        if "record attribute token statistics" in export_options:
            record_attribute_token_statistics = (
                record.get_token_statistics_by_project_id(project_id)
            )
        # without records embeddings are useless
        if "embeddings" in export_options:
            embeddings = embedding.get_finished_embeddings(project_id)
            # no need for tensors if no embeddings are exported
            if "embedding tensors" in export_options:
                embedding_tensors = embedding.get_tensors_by_project_id(project_id)
        # without records associations are useless
        if "record label associations" in export_options:
            record_label_associations = record_label_association.get_all(project_id)

            record_label_association_tokens = record_label_association.get_tokens(
                project_id
            )
            weak_supervision_task = weak_supervision.get_all(project_id)

    if "information sources" in export_options:
        information_sources = information_source.get_all(project_id)
        information_source_statistics = information_source.get_all_statistics(
            project_id
        )
        # no need for payload if no information sources are exported
        if "information sources payloads" in export_options:
            information_source_payloads = information_source.get_payloads_by_project_id(
                project_id
            )

    if "knowledge bases" in export_options:
        knowledge_bases = knowledge_base.get_all(project_id)
        terms = knowledge_term.get_terms_by_project_id(project_id)

    if "comment data" in export_options:
        comments = []
        comments += comment.get_by_all_by_category(
            enums.CommentCategory.LABELING_TASK, user_id, None, project_id, True
        )
        comments += comment.get_by_all_by_category(
            enums.CommentCategory.ATTRIBUTE, user_id, None, project_id, True
        )
        comments += comment.get_by_all_by_category(
            enums.CommentCategory.LABEL, user_id, None, project_id, True
        )
        comments += comment.get_by_all_by_category(
            enums.CommentCategory.DATA_SLICE, user_id, None, project_id, True
        )
        if "records" in export_options:
            comments += comment.get_by_all_by_category(
                enums.CommentCategory.RECORD, user_id, None, project_id, True
            )
            # only makes sense with records
            if "embeddings" in export_options:
                comments += comment.get_by_all_by_category(
                    enums.CommentCategory.EMBEDDING, user_id, None, project_id, True
                )
        if "information sources" in export_options:
            comments += comment.get_by_all_by_category(
                enums.CommentCategory.HEURISTIC, user_id, None, project_id, True
            )
        if "knowledge bases" in export_options:
            comments += comment.get_by_all_by_category(
                enums.CommentCategory.KNOWLEDGE_BASE, user_id, None, project_id, True
            )

    # -------------------- FORMATTING OF ENTITIES --------------------
    project_details_data = {
        "id": project_item.id,
        "name": project_item.name,
        "description": project_item.description,
        "tokenizer": project_item.tokenizer,
        "status": project_item.status,
    }

    records_data = [
        {
            "id": str(record_item.id),
            "data": record_item.data,
            "category": record_item.category,
        }
        for record_item in records
    ]

    attributes_data = [
        {
            "id": str(attribute_item.id),
            "name": attribute_item.name,
            "data_type": attribute_item.data_type,
            "is_primary_key": attribute_item.is_primary_key,
            "relative_position": attribute_item.relative_position,
            "user_created": attribute_item.user_created,
            "source_code": attribute_item.source_code,
            "state": attribute_item.state,
            "logs": attribute_item.logs,
            "visibility": attribute_item.visibility,
            "started_at": attribute_item.started_at,
            "finished_at": attribute_item.finished_at,
        }
        for attribute_item in attributes
    ]

    labeling_tasks_data = [
        {
            "id": str(labeling_task_item.id),
            "attribute_id": str(labeling_task_item.attribute_id),
            "name": labeling_task_item.name,
            "task_target": labeling_task_item.task_target,
            "task_type": labeling_task_item.task_type,
        }
        for labeling_task_item in labeling_tasks
    ]

    labeling_task_labels_data = [
        {
            "id": str(labeling_task_label_item.id),
            "labeling_task_id": str(labeling_task_label_item.labeling_task_id),
            "name": labeling_task_label_item.name,
            "color": labeling_task_label_item.color,
            "hotkey": labeling_task_label_item.hotkey,
        }
        for labeling_task_label_item in labeling_task_labels
    ]

    information_sources_data = [
        {
            "id": str(information_source_item.id),
            "name": information_source_item.name,
            "type": information_source_item.type,
            "return_type": information_source_item.return_type,
            "description": information_source_item.description,
            "source_code": information_source_item.source_code,
            "is_selected": information_source_item.is_selected,
            "version": information_source_item.version,
            "created_at": information_source_item.created_at,
            "labeling_task_id": information_source_item.labeling_task_id,
        }
        for information_source_item in information_sources
    ]

    record_label_associations_data = [
        {
            "id": str(record_label_association_item.id),
            "source_id": str(record_label_association_item.source_id),
            "record_id": str(record_label_association_item.record_id),
            "labeling_task_label_id": str(
                record_label_association_item.labeling_task_label_id
            ),
            "source_type": record_label_association_item.source_type,
            "return_type": record_label_association_item.return_type,
            "confidence": record_label_association_item.confidence,
            "is_gold_star": record_label_association_item.is_gold_star,
            "created_by": record_label_association_item.created_by,
            "created_at": record_label_association_item.created_at,
            "weak_supervision_id": record_label_association_item.weak_supervision_id,
            "is_valid_manual_label": record_label_association_item.is_valid_manual_label,
        }
        for record_label_association_item in record_label_associations
    ]

    weak_supervision_task_data = [
        {
            "id": str(row.id),
            "state": row.state,
            "created_at": row.created_at,
            "created_by": row.created_by,
            "finished_at": row.finished_at,
            "selected_information_sources": row.selected_information_sources,
            "selected_labeling_tasks": row.selected_labeling_tasks,
            "distinct_records": row.distinct_records,
            "result_count": row.result_count,
        }
        for row in weak_supervision_task
    ]

    knowledge_bases_data = [
        {
            "id": str(knowledge_base_item.id),
            "name": knowledge_base_item.name,
            "description": knowledge_base_item.description,
        }
        for knowledge_base_item in knowledge_bases
    ]

    embeddings_data = [
        {
            "id": str(embedding_item.id),
            "attribute_id": str(embedding_item.attribute_id),
            "name": embedding_item.name,
            "custom": embedding_item.custom,
            "type": embedding_item.type,
            "started_at": embedding_item.started_at,
            "finished_at": embedding_item.finished_at,
            "platform": embedding_item.platform,
            "model": embedding_item.model,
            "filter_attributes": embedding_item.filter_attributes,
            "additional_data": embedding_item.additional_data,
        }
        for embedding_item in embeddings
    ]

    data_slice_data = [
        {
            "id": slice_item.id,
            "created_at": slice_item.created_at,
            "created_by": slice_item.created_by,
            "name": slice_item.name,
            "filter_data": slice_item.filter_data,
            "static": slice_item.static,
            "filter_raw": slice_item.filter_raw,
            "count": slice_item.count,
            "count_sql": slice_item.count_sql,
            "slice_type": slice_item.slice_type,
            "info": slice_item.info,
        }
        for slice_item in data_slices
    ]

    data_slice_record_association_data = [
        {
            "data_slice_id": association_item.data_slice_id,
            "record_id": association_item.record_id,
            "outlier_score": association_item.outlier_score,
        }
        for association_item in data_slice_record_association
    ]

    # no need to format since db reteurns as json :)
    comment_data = comments

    # -------------------- READ AND FORMATTING OF ENTITIES WITH SQL JOINS --------------------

    record_label_association_tokens_data = [
        {
            "record_label_association_id": str(record_label_association_token_item[0]),
            "token_index": record_label_association_token_item[1],
            "is_beginning_token": record_label_association_token_item[2],
        }
        for record_label_association_token_item in record_label_association_tokens
    ]

    information_source_payloads_data = [
        {
            "id": str(payload_item[0]),
            "source_id": str(payload_item[1]),
            "created_at": payload_item[2],
            "finished_at": payload_item[3],
            "iteration": payload_item[4],
            "source_code": payload_item[5],
            "logs": payload_item[6],
            "state": payload_item[7],
        }
        for payload_item in information_source_payloads
    ]

    information_source_statistics_data = [
        {
            "id": str(statistic_item.id),
            "source_id": str(statistic_item.source_id),
            "labeling_task_label_id": str(statistic_item.labeling_task_label_id),
            "true_positives": statistic_item.true_positives,
            "false_positives": statistic_item.false_positives,
            "false_negatives": statistic_item.false_negatives,
            "record_coverage": statistic_item.record_coverage,
            "total_hits": statistic_item.total_hits,
            "source_conflicts": statistic_item.source_conflicts,
            "source_overlaps": statistic_item.source_overlaps,
        }
        for statistic_item in information_source_statistics
    ]

    record_attribute_token_statistics_data = [
        {
            "id": str(statistic_item[0]),
            "record_id": str(statistic_item[1]),
            "attribute_id": str(statistic_item[2]),
            "num_token": statistic_item[3],
        }
        for statistic_item in record_attribute_token_statistics
    ]

    terms_data = [
        {
            "knowledge_base_id": str(term_item[0]),
            "value": term_item[1],
            "comment": term_item[2],
            "blacklisted": term_item[3],
        }
        for term_item in terms
    ]

    embedding_tensors_data = [
        {
            "embedding_id": str(embedding_tensor_item[0]),
            "record_id": str(embedding_tensor_item[1]),
            "data": embedding_tensor_item[2],
            "sub_key": embedding_tensor_item[3],
        }
        for embedding_tensor_item in embedding_tensors
    ]

    # -------------------- EXPORT --------------------
    project_data = {
        "project_details_data": project_details_data,
        "records_data": records_data,
        "embeddings_data": embeddings_data,
        "embedding_tensors_data": embedding_tensors_data,
        "attributes_data": attributes_data,
        "labeling_tasks_data": labeling_tasks_data,
        "labeling_task_labels_data": labeling_task_labels_data,
        "information_sources_data": information_sources_data,
        "information_source_payloads_data": information_source_payloads_data,
        "information_source_statistics_data": information_source_statistics_data,
        "record_label_associations_data": record_label_associations_data,
        "record_label_association_tokens_data": record_label_association_tokens_data,
        "record_attribute_token_statistics_data": record_attribute_token_statistics_data,
        "knowledge_bases_data": knowledge_bases_data,
        "weak_supervision_task_data": weak_supervision_task_data,
        "terms_data": terms_data,
        "data_slice_data": data_slice_data,
        "data_slice_record_association_data": data_slice_record_association_data,
        "comments": comment_data,
    }

    logger.info(f"Finished export of project {project_id}")

    return json.dumps(project_data, default=str)


def delete_project(project_id: str) -> bool:
    project.delete_by_id(project_id, with_commit=True)
    return True


def replace_by_mappings(text: str, mappings: List[Dict[str, str]]) -> str:
    for mapping in mappings:
        for key, value in mapping.items():
            text = text.replace(str(key), str(value))
    return text


@param_throttle(seconds=2)
def send_progress_update_throttle(project_id: str, task_id: str, value: float) -> None:
    send_progress_update(project_id, task_id, value)


def send_progress_update(project_id: str, task_id: str, value: float) -> None:
    if task_id:
        notification.send_organization_update(
            project_id, f"file_upload:{task_id}:progress:{value}", is_global=True
        )


def __get_attribute_name_from_embedding_name(embedding_name: str) -> str:
    regex = "^(.+)-(?:classification|extraction).*"
    return re.match(regex, embedding_name).group(1)
