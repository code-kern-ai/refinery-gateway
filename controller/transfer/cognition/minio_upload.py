from typing import List
from submodules.model.cognition_objects import project as cognition_project
from submodules.model.business_objects import project
from submodules.model.cognition_objects import conversation
from submodules.model.enums import TaskType
from controller.task_queue import manager as task_queue_manager


def handle_cognition_file_upload(path_parts: List[str]):

    if path_parts[1] != "_cognition":
        return

    if path_parts[3] == "chat_tmp_files" and path_parts[5] == "queued":
        cognition_project_id = path_parts[2]
        conversation_id = path_parts[4]
        cognition_prj = cognition_project.get(cognition_project_id)
        if not cognition_prj:
            return

        project_id = None
        if cognition_prj.refinery_references_project_id:
            project_id = str(cognition_prj.refinery_references_project_id)
        else:
            project_id = str(
                project.get_or_create_queue_project(
                    cognition_prj.organization_id, cognition_prj.created_by, True
                ).id
            )
        conversation_item = conversation.get(cognition_project_id, conversation_id)
        if not conversation_item:
            return

        task_queue_manager.add_task(
            project_id,
            TaskType.PARSE_COGNITION_TMP_FILE,
            conversation_item.created_by,
            {
                "cognition_project_id": cognition_project_id,
                "conversation_id": conversation_id,
                "minio_path": "/".join(path_parts[1:]),
                "bucket": path_parts[0],
            },
            True,  # not sure if prio is right here as the prio tasks should only take < 1 min but waiting for the normal queue will take ages depending on the queue
        )
