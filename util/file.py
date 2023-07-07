import json
import os
import pyminizip

from typing import Any, Dict, Optional, Tuple
from zipfile import ZipFile
from exceptions.exceptions import BadPasswordError


def zip_to_json(local_file_name: str, key: Optional[str] = None) -> Dict[str, Any]:
    zip_file = ZipFile(local_file_name)
    file_name = zip_file.namelist()[0]
    if key:
        key = key.encode()
        zip_file.setpassword(key)

    try:
        data = json.loads(zip_file.read(file_name, key).decode())
        return data
    except RuntimeError as error:
        if "password" in str(error):
            raise BadPasswordError


def zip_to_json_file(zip_file_path: str, key: Optional[str] = None) -> str:
    json_data = zip_to_json(zip_file_path, key)
    file_name = __get_free_file_path(f"{zip_file_path}.json")
    with open(file_name, "w") as f:
        json.dump(json_data, f)
    return file_name


def file_to_zip(file_path: str, key: Optional[str] = None) -> Tuple[str, str]:
    zip_path = f"{file_path}.zip"
    pyminizip.compress(file_path, None, zip_path, key, 0)
    base_name = os.path.basename(file_path)
    zip_name = f"{base_name}.zip"
    return zip_path, zip_name


def text_to_json_file(text: str, base_file_name: str) -> str:
    json_file_path = f"tmp/{base_file_name}.json"
    with open(json_file_path, "w") as f:
        f.write(text)
    return json_file_path


def __get_free_file_path(file_path: str, increment: int = 1):
    check_path = file_path
    counter = 0
    while os.path.exists(check_path):
        counter += increment
        check_path = f"{file_path}_{counter}"
    return check_path
