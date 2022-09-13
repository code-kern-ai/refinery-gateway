from submodules.model.business_objects import attribute

def find_free_name(project_id: str, counter: int = 0) -> str:
    bases_count: int = attribute.count(project_id)
    name: str = f"attribute_{counter}{bases_count}"

    if attribute.get_by_name(project_id, name) is not None:
        return find_free_name(project_id, counter + 1)
    else:
        return name