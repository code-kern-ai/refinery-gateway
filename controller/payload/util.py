from submodules.model.business_objects import payload


def has_active_learner_running(project_id: str) -> bool:
    return payload.get_first_running_active_learner(project_id) is not None
