import json
from typing import Any, Dict, Optional
from zipfile import ZipFile
import random

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