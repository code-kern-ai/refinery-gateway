from submodules.model.business_objects.monitor import get_all_tasks

def monitor_all_tasks(project_id: str = None, only_running: bool = False):
        return get_all_tasks(project_id, only_running)