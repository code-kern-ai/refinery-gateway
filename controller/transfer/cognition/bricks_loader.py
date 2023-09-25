from typing import List, Dict, Optional
import requests
import json
import re

# this is a light implementation of the bricks loader, some variables etc. will error out

BASE_URL = "https://cms.bricks.kern.ai/api/modules/?pagination[pageSize]=500"

ALLOWED_VARIABLES = ["ATTRIBUTE"]

FUNCTION_REGEX = re.compile(r"^def\s(\w+)(\([a-zA-Z0-9_:\[\]=, ]*\)):$", re.MULTILINE)
VARIABLE_REGEX = re.compile(
    r"""^(([A-Z_]+):\s*(\w+)\s*=\s*(['"])*([\w\_\-\<\>]+)(['"])*)""", re.MULTILINE
)


# language not yet supported by bricks
# returns a dict of "name": "code"
def get_bricks_code_from_group(
    group_key: str,
    language_key: str,
    target_data: Dict[str, str],
    name_prefix: Optional[str] = None,
) -> Dict[str, str]:
    if not name_prefix:
        name_prefix = ""

    bricks_infos = __get_bricks_config_by_group(
        group_key,
        # "classifier",
        # True,
        language_key=language_key,
    )

    values = {
        f"{name_prefix}{b['attributes']['endpoint']}": __light_parse_bricks_code(
            b, target_data
        )
        for b in bricks_infos
    }
    return values


def __get_bricks_config_by_group(
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
        raise Exception(f"Found no entries from group {group_key}")
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


def __light_parse_bricks_code(bricks_info: dict, target_data: Dict[str, str]) -> str:
    for_ac = target_data.get("for_ac", False)
    target_name = "ac" if for_ac else "lf"

    code = bricks_info["attributes"]["sourceCodeRefinery"]
    code = __replace_function_name_in_code(code, target_name)
    code = __replace_variables_in_code(code, target_data)

    return code


def __replace_function_name_in_code(code: str, target_name: str) -> str:
    found = re.search(FUNCTION_REGEX, code)
    if not found:
        raise Exception("Could not find function in code")
    code = re.sub(FUNCTION_REGEX, f"def {target_name}{found.group(2)}:", code, 1)
    return code


def __replace_variables_in_code(code: str, target_data: Dict[str, str]) -> str:
    groups = re.findall(VARIABLE_REGEX, code)
    for found in groups:
        full_match, g1, g2, g3, g4, g5 = found
        if g1 not in ALLOWED_VARIABLES:
            raise Exception(f"Found unknown variable {g1}")
        target_name = target_data.get(g1)
        if not target_name:
            raise Exception(f"Could not find target name for {g1}")

        code = code.replace(
            full_match,
            f"{g1}: {g2} = {g3}{target_name}{g5}",
            1,
        )

    return code
