from typing import Dict, List, Union
from submodules.model import enums
from submodules.model.business_objects import labeling_task, attribute, record

INDENT_SIZE = "    "


def generate_template(
    project_id: str, labeling_task_ids: List[str], attribute_ids: List[str]
) -> str:
    return f"""<View>
{__generate_tasks(project_id,labeling_task_ids,enums.LabelingTaskType.INFORMATION_EXTRACTION)}
{__generate_attribute(project_id,attribute_ids)}
{__generate_tasks(project_id,labeling_task_ids,enums.LabelingTaskType.CLASSIFICATION)}
</View>
{__generate_example(project_id,attribute_ids)}"""


def __generate_tasks(
    project_id: str, task_ids: List[str], type: enums.LabelingTaskType
) -> str:
    tasks = labeling_task.get_task_and_label_by_ids_and_type(project_id, task_ids, type)
    if not tasks:
        return ""
    if type == enums.LabelingTaskType.INFORMATION_EXTRACTION:
        return "\n".join([__generate_extraction_task(data) for data in tasks])
    else:
        return "\n".join(
            [__generate_classification_task(project_id, data) for data in tasks]
        )


#   <Header value="Choose text sentiment"/>
#   <Labels name="label" toName="text">
#     <Label value="PER" background="red"/>
#     <Label value="ORG" background="darkorange"/>
#     <Label value="LOC" background="orange"/>
#     <Label value="MISC" background="green"/>
#   </Labels>
def __generate_extraction_task(
    task_data: Dict[str, Union[str, List[Dict[str, str]]]]
) -> List[str]:
    values = []
    values.append(
        f'{INDENT_SIZE}<Header value="Choose {task_data["attribute_name"]} {task_data["name"]}"/>'
    )
    values.append(
        f'{INDENT_SIZE}<Labels name="{task_data["name"]}" toName="{task_data["attribute_name"]}">'
    )
    values += [
        f'{INDENT_SIZE*2}<Label value="{label["name"]}" background="{label["color"]}"/>'
        for label in task_data["labels"]
    ]
    values.append(f"{INDENT_SIZE}</Labels>")

    return "\n".join(values)


#   <View style="box-shadow: 2px 2px 5px #999; padding: 20px; margin-top: 2em; border-radius: 5px;">
#     <Header value="Choose text sentiment"/>
#     <Choices name="sentiment" toName="text" choice="single" showInLine="true">
#       <Choice value="Positive"/>
#       <Choice value="Negative"/>
#       <Choice value="Neutral"/>
#     </Choices>
#   </View>
def __generate_classification_task(
    project_id: str, task_data: Dict[str, Union[str, List[Dict[str, str]]]]
) -> List[str]:
    if not task_data["attribute_name"]:
        att = attribute.get_first_useable(project_id, enums.DataTypes.TEXT)
        if att:
            task_data["attribute_name"] = att.name
        else:
            return ""
    values = []
    values.append(
        f'{INDENT_SIZE}<View style="box-shadow: 2px 2px 5px #999; padding: 20px; margin-top: 2em; border-radius: 5px;">'
    )
    values.append(
        f'{INDENT_SIZE*2}<Header value="Choose {task_data["attribute_name"]} {task_data["name"]}"/>'
    )
    values.append(
        f'{INDENT_SIZE*2}<Choices name="{task_data["name"]}" toName="{task_data["attribute_name"]}" choice="single" showInLine="true">'
    )
    values += [
        f'{INDENT_SIZE*3}<Choice value="{label["name"]}"/>'
        for label in task_data["labels"]
    ]
    values.append(f"{INDENT_SIZE*2}</Choices>")
    values.append(f"{INDENT_SIZE}</View>")

    return "\n".join(values)


#   <Text name="text_ex" value="$text_ex"/>
#   <Text name="text" value="$text"/>
def __generate_attribute(project_id: str, attribute_ids: List[str]) -> str:
    attributes = attribute.get_all(project_id)
    values = []
    for att in attributes:
        if str(att.id) in attribute_ids:
            values.append(f'{INDENT_SIZE}<Text name="{att.name}" value="${att.name}"/>')
    return "\n".join(values)


# <!-- {
#   "data": {
#       "text": "A great 3D mace that delivers everything almost right in your face."
#  }
# } -->
def __generate_example(project_id: str, attribute_ids: List[str]) -> str:
    attributes = attribute.get_all(project_id)
    example_record = record.get_one(project_id)
    values = []
    values.append("<!-- {")
    values.append(f'{INDENT_SIZE}"data": {{')
    data = []
    for att in attributes:
        if str(att.id) in attribute_ids:
            data.append(
                f'{INDENT_SIZE*2}"{att.name}": "{example_record.data[att.name]}"'
            )
    values.append(",\n".join(data))
    values.append(f"{INDENT_SIZE}}}")
    values.append("} -->")
    return "\n".join(values)
