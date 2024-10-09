from submodules.model.business_objects import embedding


def has_encoder_running(project_id: str) -> bool:
    return embedding.get_first_running_encoder(project_id) is not None
