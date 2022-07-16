from controller.weak_supervision import weak_supervision_service
from util.decorator import debounce

# TODO check which of these methods are still needed and remove not needed ones
def set_information_source_quality_statistics_by_source_id(source_id: str):
    weak_supervision_service.calculate_quality_stats_by_source_id(source_id)


# for the same function parameter the function call is debounced for t seconds given as wait argument
# if for 10 sec nothing happens for the task the statistics are calculated
# since this is only relevant for changing record label associations as own function
@debounce(10)
def set_information_source_statistics_by_labeling_task_id_debounce(
    labeling_task_id, method
):
    set_information_source_statistics_by_labeling_task_id(labeling_task_id, method)


def set_information_source_statistics_by_labeling_task_id(labeling_task_id, method):
    weak_supervision_service.calculate_method_stats_by_labeling_task_id(
        labeling_task_id, method
    )
