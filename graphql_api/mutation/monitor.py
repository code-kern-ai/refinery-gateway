import graphene
from controller.auth import manager as auth
from controller.monitor import manager
from submodules.model import enums


class CancelTask(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        task_id = graphene.ID(required=True)
        task_type = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, task_id: str, task_type: str):
        auth.check_admin_access(info)
        if task_type == enums.TaskType.ATTRIBUTE_CALCULATION.value:
            manager.cancel_attribute_calculation(project_id, task_id)
        elif task_type == enums.TaskType.EMBEDDING.value:
            manager.cancel_embedding(project_id, task_id)
        elif task_type == enums.TaskType.INFORMATION_SOURCE.value:
            manager.cancel_information_source_payload(project_id, task_id)
        elif task_type == enums.TaskType.TOKENIZATION.value:
            manager.cancel_record_tokenization_task(project_id, task_id)
        elif task_type == enums.TaskType.UPLOAD_TASK.value:
            manager.cancel_upload_task(project_id, task_id)
        elif task_type == enums.TaskType.WEAK_SUPERVISION.value:
            manager.cancel_weak_supervision(project_id, task_id)
        else:
            raise ValueError(f"{task_type} is no valid task type")
        return CancelTask(ok=True)


class CancelAllRunningTasks(graphene.Mutation):
    ok = graphene.Boolean()

    def mutate(self, info):
        auth.check_admin_access(info)
        manager.cancel_all_running_tasks()
        return CancelAllRunningTasks(ok=True)


class CancelInformationSourcePayload(graphene.Mutation):
    class Arguments:
        payload_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, payload_id: str):
        auth.check_admin_access(info)
        manager.cancel_information_source_payload(payload_id=payload_id)
        return CancelInformationSourcePayload(ok=True)


class CancelUploadTaskTask(graphene.Mutation):
    class Arguments:
        task_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, task_id: str):
        auth.check_admin_access(info)
        manager.cancel_upload_task(upload_task_id=task_id)
        return CancelUploadTaskTask(ok=True)


class CancelWeakSupervisionTask(graphene.Mutation):
    class Arguments:
        payload_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, payload_id: str):
        auth.check_admin_access(info)
        manager.cancel_weak_supervision(payload_id=payload_id)
        return CancelWeakSupervisionTask(ok=True)


class CancelAttributeCalculationTask(graphene.Mutation):
    class Arguments:
        attribute_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, attribute_id: str):
        auth.check_admin_access(info)
        manager.cancel_attribute_calculation(attribute_id=attribute_id)
        return CancelAttributeCalculationTask(ok=True)


class CancelEmbeddingTask(graphene.Mutation):
    class Arguments:
        embedding_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, embedding_id: str):
        auth.check_admin_access(info)
        manager.cancel_embedding(embedding_id=embedding_id)
        return CancelEmbeddingTask(ok=True)


class CancelTokenizationTask(graphene.Mutation):
    class Arguments:
        task_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, task_id: str):
        auth.check_admin_access(info)
        manager.cancel_record_tokenization_task(tokenization_task_id=task_id)
        return CancelTokenizationTask(ok=True)


class MonitorMutation(graphene.ObjectType):
    cancel_task = CancelTask.Field()
    cancel_all_running_tasks = CancelAllRunningTasks.Field()
    cancel_information_source_payload = CancelInformationSourcePayload.Field()
    cancel_upload_task = CancelUploadTaskTask.Field()
    cancel_weak_supervision_task = CancelWeakSupervisionTask.Field()
    cancel_attribute_calculation_task = CancelAttributeCalculationTask.Field()
    cancel_tokenization_task = CancelTokenizationTask.Field()
    cancel_embedding_task = CancelEmbeddingTask.Field()
