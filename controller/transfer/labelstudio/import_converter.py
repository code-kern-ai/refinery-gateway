import json
from controller.transfer.record_transfer_manager import download_file
from submodules.model import enums
from submodules.model.business_objects import upload_task


def manage_converting_data(project_id: str, task_id: str) -> None:
    task = upload_task.get(project_id, task_id)
    file_path = download_file(project_id, task)
    mappings = json.loads(task.mappings)
    user_mapping = mappings.get("users")
    attribute_task_mapping = mappings.get("tasks")

    converted_data = None
    with open(file_path) as file:
        data = json.load(file)
        converted_data = __extract_and_compose_data(
            data, user_mapping, attribute_task_mapping
        )

    with open(f"{task.id}_converted_file.json", "w") as file:
        file.write(json.dumps(converted_data))


def __extract_and_compose_data(data, user_mapping, attribute_task_mapping):

    print("user_mapping", user_mapping)
    print("attribute_task_mapping", attribute_task_mapping)

    records = []
    for record_item in data:
        record = {"label_studio_id": record_item.get("id")}

        for attribute in record_item.get("data").keys():
            record[attribute] = record_item.get("data").get(attribute)
        for annotation_item in record_item.get("annotations"):
            for result in annotation_item["result"]:

                if (
                    user_mapping.get(str(annotation_item.get("completed_by")))
                    == enums.RecordImportMappingValues.IGNORE.value
                ):
                    continue

                if result.get("type") != "choices":
                    continue

                task_name = result.get("from_name")
                table_name_label = f"__{task_name}__MANUAL"

                if (
                    attribute_task_mapping.get(task_name)
                    == enums.RecordImportMappingValues.ATTRIBUTE_SPECIFIC.value
                ):
                    table_name_label = f"{result.get('to_name')}{table_name_label}"

                table_name_created_by = f"{table_name_label}__CREATED_BY"

                record[table_name_label] = result.get("value").get("choices")[0]
                record[table_name_created_by] = user_mapping.get(
                    str(annotation_item.get("completed_by"))
                )

        records.append(record)

    return records
