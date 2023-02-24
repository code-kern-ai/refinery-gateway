from submodules.model.business_objects import monitor


def monitor_all_tasks(project_id: str = None, only_running: bool = False):
    return monitor.get_all_tasks(project_id, only_running)


def cancel_all_running_tasks(project_id: str = None):
    monitor.cancel_all_running_tasks(project_id)


def cancel_upload_task(project_id: str = None, upload_task_id: str = None):
    monitor.set_upload_task_to_failed(project_id, upload_task_id, True)


def cancel_weak_supervision(project_id: str = None, payload_id: str = None):
    monitor.set_weak_supervision_to_failed(project_id, payload_id, True)


def cancel_attribute_calculation(project_id: str = None, attribute_id: str = None):
    monitor.set_attribute_calculation_to_failed(project_id, attribute_id, True)


def cancel_embedding(project_id: str = None, embedding_id: str = None):
    monitor.set_embedding_to_failed(project_id, embedding_id, True)


def cancel_information_source_payload(project_id: str = None, payload_id: str = None):
    monitor.set_information_source_payloads_to_failed(project_id, payload_id, True)


def cancel_record_tokenization_task(
    project_id: str = None, tokenization_task_id: str = None
):
    monitor.set_record_tokenization_task_to_failed(
        project_id, tokenization_task_id, True
    )
