import json
import os
import random
import pyminizip

from typing import Any, Dict, Optional, Tuple
from zipfile import ZipFile

def zip_to_json(local_file_name: str, key: Optional[str] = None) -> Dict[str, Any]:
    zip_file = ZipFile(local_file_name)
    file_name = zip_file.namelist()[0]
    if key:
        key = key.encode()
        zip_file.setpassword(key)
    return json.loads(zip_file.read(file_name, key).decode())

def zip_to_json_file(zip_file_path: str, key: Optional[str] = None) -> str:
    json_data = zip_to_json(zip_file_path, key)
    file_name = f"{zip_file_path}{random.randint(1,999)}.json" 
    with open(file_name, 'w') as f:
        json.dump(json_data, f)
    return file_name


def file_to_zip(file_path: str, key: Optional[str] = None) -> Tuple[str, str]:
    zip_path= f"{file_path}.zip"
    pyminizip.compress(file_path, None, zip_path, key, 0)
    base_name = os.path.basename(file_path)
    zip_name = f"{base_name}.zip"
    return zip_path, zip_name

def json_string_to_file(json_string: str, base_file_name: str, key: Optional[str] = None) -> str:
    json_file_path = f"tmp/{base_file_name}.json"
    with open(json_file_path, 'w') as f:
        json.dump(json_string, f)
    return json_file_path
