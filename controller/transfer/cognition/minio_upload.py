from typing import List
from submodules.model.cognition_objects import project as cognition_project
from submodules.model.cognition_objects import conversation
from submodules.model.enums import TaskType
from controller.task_master import manager as task_master_manager


def handle_cognition_file_upload(path_parts: List[str]):

    if path_parts[1] != "_cognition":
        return

    if path_parts[3] == "chat_tmp_files" and path_parts[5] == "queued":
        cognition_project_id = path_parts[2]
        conversation_id = path_parts[4]
        cognition_prj = cognition_project.get(cognition_project_id)
        if not cognition_prj:
            return

        conversation_item = conversation.get(cognition_project_id, conversation_id)
        if not conversation_item:
            return

        task_master_manager.queue_task(
            str(cognition_prj.organization_id),
            str(conversation_item.created_by),
            TaskType.PARSE_COGNITION_TMP_FILE,
            {
                "cognition_project_id": str(cognition_project_id),
                "conversation_id": str(conversation_id),
                "minio_path": "/".join(path_parts[1:]),
                "bucket": path_parts[0],
            },
            True,  # not sure if prio is right here as the prio tasks should only take < 1 min but waiting for the normal queue will take ages depending on the queue
        )
