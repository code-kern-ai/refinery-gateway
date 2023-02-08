from submodules.model.business_objects import knowledge_base, knowledge_term
import re


def find_free_name(project_id: str, counter: int = 0) -> str:
    bases_count: int = knowledge_base.count(project_id)
    name: str = f"knowledge_base_{counter}{bases_count}"

    if knowledge_base.get_by_name(project_id, name) is not None:
        return find_free_name(project_id, counter + 1)
    else:
        return name


def create_knowledge_base_if_not_existing(name: str, project_id: str) -> None:
    if not knowledge_base.get_by_name(project_id, name):
        knowledge_base.create(project_id, name)


def build_knowledge_base_from_project(project_id: str) -> str:
    knowledge_bases_dict = {}
    knowledge_base_source: str = ""

    for knowledge_base_item in knowledge_base.get_all_by_project_id(project_id):
        knowledge_bases_dict[resolve_name_as_variable(knowledge_base_item.name)] = []

    for term, knowledge_base_item in knowledge_term.get_terms_with_base_names(
        project_id
    ):
        knowledge_bases_dict[resolve_name_as_variable(knowledge_base_item)].append(
            term
        )  # use here knowledge base name in standard format (underscore and )

    for knowledge_base_item, values in knowledge_bases_dict.items():
        knowledge_base_source += f"\n{knowledge_base_item} = [\n"
        for value in values:
            value: str = value.replace("'", "\\'")  # e.g. "You're too good to me"
            knowledge_base_source += f"\t'{value}',\n"
        knowledge_base_source += "]"
    return knowledge_base_source


def resolve_name_as_variable(name: str, prefix: str = "_") -> str:
    name = name.lower().replace(" ", "_")
    name = re.sub("[^\w]", "", name).strip()
    return (prefix + name) if name[0].isdigit() else name
