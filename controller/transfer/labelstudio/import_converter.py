import json
from controller.transfer.record_transfer_manager import download_file
from submodules.model.business_objects import upload_task


def manage_converting_data(project_id: str, task_id: str) -> None:
    task = upload_task.get(project_id, task_id)
    file_path = download_file(project_id, task)
    mappings = json.loads(task.mappings)
    user_mapping = mappings.get("user")
    attribute_task_mapping = mappings.get("tasks")

    with open(file_path, "w+") as file:
        if task.file_type == "JSON":
            data = json.load(file)
            converted_data = __extract_and_compose_data(data, user_mapping, attribute_task_mapping)
            file.write(json.dumps(converted_data))
            print("path", file_path)


def __extract_and_compose_data(data, user_mapping, attribute_task_mapping):
    records = []
    for record_item in data:
        record = {
            "label_studio_id": record_item.get("id"),
            "data": record_item.get("data"),
        }

        for attribute in record_item.get("data").keys():
            record[attribute] = record_item.get("data").get(attribute)
        for annotation_item in record_item.get("annotations"):
            if annotation_item.get("type") != "choices":
                continue

            task_name = annotation_item.get("from_name")
            table_name_label = f"__{task_name}__MANUAL"

            if attribute_task_mapping.get(task_name) == "ATTRIBUTE_SPECIFIC": # TODO ENUMS
                table_name_label = f"{attribute_task_mapping.get(task_name)}{table_name_label}"

            table_name_created_by = f"{table_name_label}__CREATED_BY"

            record[table_name_label] = annotation_item.get("value").get("choices")
            record[table_name_created_by] = user_mapping.get(
                annotation_item.get("completed_by")
            )

        records.append(record)

    return records

