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
VARIABLE_REGEX = re.compile(
    r"""^(([A-Z_]+):\s*(\w+)\s*=\s*(['"])*([\w\_\-\<\>]+)(['"])*)""", re.MULTILINE
)


# language not yet supported by bricks
# returns a dict of "name": "code"
def get_bricks_code_from_group(
    project_id: str,
    group_key: str,
    bricks_type: str,  # "classifier" or "extractor" or "generator"
    language_key: str,
    target_data: Dict[str, str],
    name_prefix: Optional[str] = None,
) -> Dict[str, str]:
    if not name_prefix:
        name_prefix = ""

    bricks_infos = __get_bricks_config_by_group(
        project_id,
        group_key,
        bricks_type,
        language_key=language_key,
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
    project_id: str,
    group_key: str,
    module_type: str = "classifier",
    only_python: bool = True,
    language_key: Optional[str] = None,
) -> List[Dict]:
    url = BASE_URL + "&filters[moduleType][$eq]=" + module_type
    if only_python:
        url += "&filters[executionType][$eq]=pythonFunction"
    url += '&filters[partOfGroup][$contains]="' + group_key + '"'
    if language_key:
        url += "&filters[language][$in][0]=multi"
        url += "&filters[language][$in][0]=" + language_key
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception("Could not load bricks from CMS")

    bricks_info = response.json()
    data = bricks_info["data"]
    if len(data) == 0:
        send_log_message(
            project_id, f"Found no entries from bricks group {group_key}", True
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
    for_ac = target_data.get("for_ac", False)
    cognition_mapping = __parse_cognition_mapping(bricks_info, target_data)

    target_name = "ac" if for_ac else "lf"

    code = bricks_info["attributes"]["sourceCodeRefinery"]
    code = __replace_function_name_in_code(
        code, target_name, cognition_mapping is not None
    )
    code = __replace_variables_in_code(code, target_data)

    if cognition_mapping:
        code = __extend_code_by_mapping(code, cognition_mapping)

    return code


def __parse_cognition_mapping(
    bricks_info: Dict[str, Any], target_data: Dict[str, str]
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
