from submodules.model.business_objects import monitor


def monitor_all_tasks(project_id: str = None, only_running: bool = False):
    return monitor.get_all_tasks(project_id, only_running)


def cancel_all_running_tasks(project_id: str = None):
    return monitor.cancel_all_running_tasks(project_id)
