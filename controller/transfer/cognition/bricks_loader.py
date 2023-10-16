from typing import List, Dict, Optional, Any
import requests
import json
import re
from .wizard_function_templates import MAPPING_WRAPPER
from .util import send_log_message

# this is a light implementation of the bricks loader, some variables etc. will error out

BASE_URL = "https://cms.bricks.kern.ai/api/modules/?pagination[pageSize]=500"

FUNCTION_REGEX = re.compile(
    r"^def\s(\w+)(\([a-zA-Z0-9_:\[\]=, ]*\)):\s*$", re.MULTILINE
)
CLASS_REGEX = re.compile(r"^class ([\w]+)\(([^)]+)\):$", re.MULTILINE)
VARIABLE_REGEX = re.compile(
    r"""^(([A-Z_]+):\s*(\w+)\s*=\s*(['"])*([\w\_\-\<\>]+)(['"])*)""", re.MULTILINE
)

AL_BACKEND_NAME = "ATLClassifier"
LF_BACKEND_NAME = "lf"
AC_BACKEND_NAME = "ac"


# language not yet supported by bricks
# returns a dict of "name": {"code": "code", "endpoint": "endpoint"}
def get_bricks_code_from_group(
    group_key: str,
    bricks_type: str,  # "classifier" or "extractor" or "generator"
    language_key: str,
    target_data: Dict[str, str],
    name_prefix: Optional[str] = None,
    project_id: Optional[str] = None,
) -> Dict[str, str]:
    if not name_prefix:
        name_prefix = ""
    bricks_infos = __get_bricks_config_by_group(
        group_key,
        bricks_type,
        active_learner=target_data.get("target_type") == "al",
        language_key=language_key,
        project_id=project_id,
    )

    values = {
        f"{name_prefix}{b['attributes']['endpoint']}": {
            "code": __light_parse_bricks_code(b, target_data),
            "endpoint": b["attributes"]["endpoint"],
        }
        for b in bricks_infos
    }
    return values


def __get_bricks_config_by_group(
    group_key: str,
    module_type: str = "classifier",
    active_learner: bool = False,
    language_key: Optional[str] = None,
    project_id: Optional[str] = None,
) -> List[Dict]:
    url = BASE_URL + "&filters[moduleType][$eq]=" + module_type
    execution_type = "activeLearner" if active_learner else "pythonFunction"
    url += "&filters[executionType][$eq]=" + execution_type

    url += '&filters[partOfGroup][$contains]="' + group_key + '"'
    if language_key:
        url += "&filters[language][$in][0]=multi"
        url += "&filters[language][$in][0]=" + language_key

    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("Could not load bricks from CMS")

    bricks_info = response.json()
    data = bricks_info["data"]
    if len(data) == 0 and project_id:
        send_log_message(
            project_id,
            f"Found no entries from bricks group {group_key} - executionType {execution_type}",
            True,
        )
    for bricks_info in data:
        bricks_info["attributes"]["integratorInputs"] = json.loads(
            bricks_info["attributes"]["integratorInputs"]
        )
    return data


# for singular bricks (e.g. language detection)
def get_bricks_code_from_endpoint(endpoint: str, target_data: Dict[str, str]) -> str:
    bricks_info = __get_bricks_config_by_endpoint_name(endpoint)
    return __light_parse_bricks_code(bricks_info, target_data)


def __get_bricks_config_by_endpoint_name(endpoint: str) -> Dict:
    url = BASE_URL + "&filters[endpoint][$eq]=" + endpoint
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("Could not load bricks from CMS")

    bricks_info = response.json()
    data = bricks_info["data"]
    if len(data) != 1:
        raise Exception(
            f"Found {len(data)} entries from endpoint {endpoint} expected exactly 1"
        )
    bricks_info = data[0]
    bricks_info["attributes"]["integratorInputs"] = json.loads(
        bricks_info["attributes"]["integratorInputs"]
    )
    return bricks_info


def __light_parse_bricks_code(
    bricks_info: Dict[str, Any], target_data: Dict[str, str]
) -> str:
    deletion_keys = []
    cognition_mapping = __parse_cognition_mapping(
        bricks_info, target_data, deletion_keys
    )
    has_mapping = cognition_mapping is not None and len(cognition_mapping.keys()) > 0

    target_name = __get_target_name(target_data)

    code = bricks_info["attributes"]["sourceCodeRefinery"]

    if target_name == AL_BACKEND_NAME:
        code = __replace_class_name_in_code(code, target_name)
    else:
        code = __replace_function_name_in_code(code, target_name, has_mapping)

    code = __replace_variables_in_code(code, target_data)

    if has_mapping:
        code = __extend_code_by_mapping(code, cognition_mapping)
    for key in deletion_keys:
        del target_data[key]
    return code


def __get_target_name(target_data: Dict[str, str]) -> str:
    target_type = target_data.get("target_type", "lf")
    if target_type == "lf":
        return LF_BACKEND_NAME
    elif target_type == "ac":
        return AC_BACKEND_NAME
    elif target_type == "al":
        return AL_BACKEND_NAME
    else:
        raise Exception(f"Unknown target type {target_type}")


def __parse_cognition_mapping(
    bricks_info: Dict[str, Any], target_data: Dict[str, str], deletion_keys: List[str]
) -> Optional[Dict[str, str]]:
    mapping_string = bricks_info["attributes"].get("cognitionInitMapping")
    if not mapping_string:
        return None
    cognition_mapping = json.loads(mapping_string)
    if cognition_mapping:
        keys = list(cognition_mapping.keys())
        for key in keys:
            if cognition_mapping[key] == "null":
                cognition_mapping[key] = None
            # items with @@<name>@@ are default values not actual mapping
            if key.startswith("@@") and key.endswith("@@"):
                target_data[key[2:-2]] = cognition_mapping[key]
                del cognition_mapping[key]
                deletion_keys.append(key[2:-2])
    return cognition_mapping


def __replace_function_name_in_code(
    code: str, target_name: str, has_mapping: bool
) -> str:
    found = re.search(FUNCTION_REGEX, code)
    if not found:
        raise Exception("Could not find function in code")

    new_fn_name = target_name
    mapping_extension = ""
    if has_mapping:
        new_fn_name = "bricks_base_function"
        mapping_extension = MAPPING_WRAPPER.replace("@@target_name@@", target_name)

    replace_code = f"{mapping_extension}\ndef {new_fn_name}{found.group(2)}:"

    code = re.sub(FUNCTION_REGEX, replace_code, code, 1)
    return code


def __replace_class_name_in_code(code: str, target_name: str) -> str:
    found = re.search(CLASS_REGEX, code)
    if not found:
        raise Exception("Could not find class in code")

    replace_code = f"class {target_name}({found.group(2)}):"

    code = re.sub(CLASS_REGEX, replace_code, code, 1)
    return code


def __replace_variables_in_code(code: str, target_data: Dict[str, str]) -> str:
    groups = re.findall(VARIABLE_REGEX, code)
    for found in groups:
        full_match, g1, g2, g3, g4, g5 = found
        target_name = target_data.get(g1)
        if not target_name:
            # no value to set so default code is used
            continue

        code = code.replace(
            full_match,
            f"{g1}: {g2} = {g3}{target_name}{g5}",
            1,
        )

    return code


def __extend_code_by_mapping(code: str, mapping: Dict[str, str]):
    mapping_block = "#generated by the bricks integrator\nmy_custom_mapping = {"
    for key in mapping:
        mapping_block += f'\n    "{key}": '
        if mapping[key]:
            mapping_block += f'"{mapping[key]}"'
        else:
            mapping_block += "None"
        mapping_block += ","
    mapping_block += "\n}"
    return code + "\n\n" + mapping_block
