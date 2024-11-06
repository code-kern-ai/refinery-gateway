import os
from typing import Any, List

from controller.knowledge_base import util as knowledge_base
import docker
from controller.tokenization import manager as tokenization_manager
import pickle
import tarfile
from submodules.model.business_objects import record
from submodules.model.business_objects.record import get_tokenized_record_from_db
import time
import uuid

from submodules.model import daemon

client = docker.from_env()
image = os.getenv("RECORD_IDE_IMAGE")
exec_env_network = os.getenv("LF_NETWORK")

__containers_running = {}


def copy_to(src: str, dst: str, tar_path: str) -> None:
    # https://stackoverflow.com/questions/46390309/how-to-copy-a-file-from-host-to-container-using-docker-py-docker-sdk
    name, dst = dst.split(":")
    container = client.containers.get(name)

    os.chdir(os.path.dirname(src))
    srcname = os.path.basename(src)
    with tarfile.open(tar_path, "w") as tar:
        try:
            tar.add(srcname)
        finally:
            tar.close()

    with open(tar_path, "rb") as file:
        container.put_archive(path="/", data=file)


def run_record_ide(
    user_id: str, project_id: str, record_id: str, code: str
) -> List[str]:
    record_bytes_path = pack_record_data(project_id, record_id)
    knowledge_base_bytes_path = pack_knowledge_base(project_id)

    command = [code, record_bytes_path, knowledge_base_bytes_path]
    cpu_limit = docker.types.Ulimit(name="cpu", soft=50, hard=50)
    container_name = str(uuid.uuid4())
    container = client.containers.create(
        command=command,
        name=container_name,
        image=image,
        detach=True,
        network=exec_env_network,
        ulimits=[cpu_limit],
    )
    error = ""
    try:
        record_tar_path = f"{record_id}.tar"
        knowledge_base_tar_path = f"{project_id}.tar"

        copy_to(
            f"./{record_bytes_path}",
            f"{container.name}:/{record_bytes_path}",
            record_tar_path,
        )
        copy_to(
            f"./{knowledge_base_bytes_path}",
            f"{container.name}:/{knowledge_base_bytes_path}",
            knowledge_base_tar_path,
        )
        daemon.run_without_db_token(cancel_container, container_name, container)
        __containers_running[container_name] = True
        container.start()
        logs_arr = [
            line.decode("utf-8").strip("\n")
            for line in container.logs(
                stream=True, stdout=True, stderr=True, timestamps=False
            )
        ]
        logs = "\n".join(logs_arr)
        if logs_arr:
            last_log = logs_arr[-1]
            if "Killed" in last_log and "/usr/local/bin/python run_ide.py" in last_log:
                error = "cpu time"

    finally:
        if not __containers_running[container_name]:
            error = "run time"
        else:
            container.stop()
        container.remove()
        os.remove(record_bytes_path)
        os.remove(record_tar_path)
        os.remove(knowledge_base_bytes_path)
        os.remove(knowledge_base_tar_path)

        if error:
            logs += f"\n\nUnfortunatly the {error} was exceeded.\n\nIf this is not by mistake an infinite loop situation please contact our support."
    del __containers_running[container_name]
    return logs


def cancel_container(name: str, container: Any):
    TIMEOUT = 60
    time.sleep(TIMEOUT)
    if name in __containers_running and __containers_running[name]:
        __containers_running[name] = False
        container.stop()
        print(f"Cancelled coontainer {name} after {TIMEOUT} sec", flush=True)


def container_exists(containers: Any, name: str) -> bool:
    try:
        return containers.get(name) is not None
    except docker.errors.NotFound:
        pass
    return False


def pack_record_data(project_id: str, record_id: str) -> str:
    tokenized_record = get_tokenized_record_from_db(project_id, record_id)
    if not tokenized_record:
        return None
    used_columns = {value for value in tokenized_record.columns}

    full_data = tokenization_manager.__get_docs_from_db(project_id, record_id)

    record_data = record.get(project_id, record_id).data
    for c in record_data:
        if c not in used_columns:
            full_data[c] = record_data[c]

    record_bytes_path = f"{record_id}record_bytes.p"
    with open(record_bytes_path, "wb") as file:
        pickle.dump(full_data, file)
    return record_bytes_path


def pack_knowledge_base(project_id: str) -> str:
    knowledge_base_source = knowledge_base.build_knowledge_base_from_project(project_id)
    knowledge_base_path = f"{project_id}knowledge_base.p"
    with open(knowledge_base_path, "wb") as file:
        pickle.dump(knowledge_base_source, file)
    return knowledge_base_path
