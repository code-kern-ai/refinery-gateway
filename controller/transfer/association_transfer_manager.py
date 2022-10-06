import traceback
from typing import Dict, Any, List
from controller.labeling_task import manager as labeling_task_manager
from controller.attribute import manager as attribute_manager
from controller.record import manager as record_manager
from util import notification


from controller.information_source import manager as information_source_manager
from submodules.model import enums
from submodules.model.business_objects import (
    general,
    labeling_task_label,
    record_label_association,
)
from submodules.model.models import RecordLabelAssociation
from controller.weak_supervision import weak_supervision_service as weak_supervision


def import_associations(
    project_id: str,
    user_id: str,
    model_name: str,
    labeling_task_name: str,
    associations: Dict[str, Any],
    indices: List[Dict[str, Any]],
    source_type: str,
) -> int:
    labeling_task = labeling_task_manager.get_labeling_task_by_name(
        project_id, labeling_task_name
    )

    information_source = information_source_manager.get_information_source_by_name(
        project_id, model_name
    )

    if information_source is None:

        if source_type == "model_callback":
            description = "This is a model callback"
            type = enums.LabelSource.MODEL_CALLBACK.value
        elif source_type == "heuristic":
            description = "This is a heuristic"
            type = enums.LabelSource.INFORMATION_SOURCE.value
        else:
            raise Exception("Unknown source type")

        information_source = information_source_manager.create_information_source(
            project_id,
            user_id,
            labeling_task.id,
            model_name,
            "",
            description,
            type,
        )
        notification.send_organization_update(
            project_id, f"information_source_created:{str(information_source.id)}"
        )

    attribute_names = list(indices[0].keys())
    attribute_list = attribute_manager.get_all_attributes_by_names(
        project_id, attribute_names
    )

    records = record_manager.get_records_by_composite_keys(
        project_id,
        indices,
        attribute_list,
        enums.RecordCategory.SCALE.value,  # we currently don't use TEST any more
    )
    record_ids = [record.id for record in list(records.values())]

    record_label_associations = []

    label_options = labeling_task_label.get_all_by_task_id(project_id, labeling_task.id)
    label_id_by_name_dict = {label.name: label.id for label in label_options}
    for record_id, association in zip(record_ids, associations):
        label_name, confidence = association
        record_label_associations.append(
            RecordLabelAssociation(
                project_id=project_id,
                record_id=record_id,
                labeling_task_label_id=label_id_by_name_dict[label_name],
                source_type=enums.LabelSource.MODEL_CALLBACK.value,
                source_id=information_source.id,
                return_type=enums.InformationSourceReturnType.RETURN.value,
                confidence=confidence,
                created_by=user_id,
            )
        )

    record_label_association.delete_by_source_id_and_record_ids(
        project_id, information_source.id, record_ids
    )
    general.add_all(record_label_associations, with_commit=True)
    general.commit()

    try:
        weak_supervision.calculate_stats_after_source_run_with_debounce(
            project_id, information_source.id, user_id
        )
    except:
        print(traceback.format_exc())

    return len(record_label_associations)
