from typing import Dict, List


def get_black_white_demo() -> Dict[str, List[str]]:
    global __whitelist_mutation_demo_parsed
    global __blacklist_query_demo_parsed

    if not __whitelist_mutation_demo_parsed:
        __parse_black_white_list()
    toReturn = {"mutations": [], "queries": []}
    for v in __whitelist_mutation_demo_parsed:
        toReturn["mutations"].append(v)
    for v in __blacklist_query_demo_parsed:
        toReturn["queries"].append(v)

    return toReturn


def __snake_case_to_camel_case(str: str):
    # GraphQL uses camel case for resolving
    return "".join(
        [
            word.title() if idx > 0 else word.lower()
            for idx, word in enumerate(str.split("_"))
        ]
    )


def __parse_black_white_list():
    global __whitelist_mutation_demo
    global __blacklist_query_demo
    global __whitelist_mutation_demo_parsed
    global __blacklist_query_demo_parsed

    tmp = {}
    for v in __whitelist_mutation_demo:
        tmp[v[0].lower() + v[1:]] = v
    __whitelist_mutation_demo_parsed = tmp
    tmp = {}
    for v in __blacklist_query_demo:
        tmp[__snake_case_to_camel_case(v)] = v
    __blacklist_query_demo_parsed = tmp


# CAUTION: this is not necessarily the class name but often times similar or equal. This is the schema name we would use in gql
__whitelist_mutation_demo = {
    "CreateDataSlice",
    "UpdateDataSlice",
    "DeleteDataSlice",
    "CreateOutlierSlice",
    "UpdateSliceTypeManual",
    "CreateInformationSource",
    # "DeleteInformationSource",
    "ToggleInformationSource",
    "SetAllInformationSourceSelected",
    "CreateZeroShotInformationSource",
    # "UpdateInformationSource",
    "CreateKnowledgeBase",
    # "DeleteKnowledgeBase",
    # "UpdateKnowledgeBase",
    "AddTermToKnowledgeBase",
    "PasteKnowledgeTerms",
    "UpdateKnowledgeTerm",
    "DeleteKnowledgeTerm",
    "BlacklistTerm",
    # "CreateLabelingTaskLabel",
    "UpdateLabelColor",
    "UpdateLabelHotkey",
    # "DeleteLabelingTaskLabel",
    "PostEvent",
    "CreateNotification",
    "AddClassificationLabelsToRecord",
    "AddExtractionLabelToRecord",
    "SetGoldStarAnnotationForTask",
    "DeleteRecordLabelAssociationByIds",
    "DeleteGoldStarAssociationForTask",
    "UpdateRlaIsValidManual",
}


# Function names without resolve_
__blacklist_query_demo = {
    "upload_credentials_and_id",
    "upload_task_by_id",
    "prepare_project_export",
}


# Parsed to a dict with gql query names
__whitelist_mutation_demo_parsed = None
__blacklist_query_demo_parsed = None
