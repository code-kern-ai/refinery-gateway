import json
from typing import Any, Dict, Optional
from zipfile import ZipFile
import pyminizip
from util import security


def zip_to_json(local_file_name: str, key: Optional[str] = None) -> Dict[str, Any]:
    zip_file = ZipFile(local_file_name)
    file_name = zip_file.namelist()[0]
    if key:
        key = key.encode()
        zip_file.setpassword(key)
    return json.loads(zip_file.read(file_name, key).decode())
