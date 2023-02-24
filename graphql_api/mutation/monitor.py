import graphene
from controller.auth import manager as auth
from controller.monitor import manager


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

    def mutate(self, info, payload_id):
        auth.check_admin_access(info)
        manager.cancel_information_source_payload(payload_id=payload_id)
        return CancelInformationSourcePayload(ok=True)


class CancelUploadTaskTask(graphene.Mutation):
    class Arguments:
        task_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, task_id):
        auth.check_admin_access(info)
        manager.cancel_upload_task(upload_task_id=task_id)
        return CancelUploadTaskTask(ok=True)


class CancelWeakSupervisionTask(graphene.Mutation):
    class Arguments:
        payload_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, payload_id):
        auth.check_admin_access(info)
        manager.cancel_weak_supervision(payload_id=payload_id)
        return CancelWeakSupervisionTask(ok=True)


class CancelAttributeCalculationTask(graphene.Mutation):
    class Arguments:
        attribute_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, attribute_id):
        auth.check_admin_access(info)
        manager.cancel_attribute_calculation(attribute_id=attribute_id)
        return CancelAttributeCalculationTask(ok=True)


class CancelEmbeddingTask(graphene.Mutation):
    class Arguments:
        embedding_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, embedding_id):
        auth.check_admin_access(info)
        manager.cancel_embedding(embedding_id=embedding_id)
        return CancelEmbeddingTask(ok=True)


class CancelTokenizationTask(graphene.Mutation):
    class Arguments:
        task_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, task_id):
        auth.check_admin_access(info)
        manager.cancel_record_tokenization_task(tokenization_task_id=task_id)
        return CancelTokenizationTask(ok=True)


class MonitorMutation(graphene.ObjectType):
    cancel_all_running_tasks = CancelAllRunningTasks.Field()
    cancel_information_source_payload = CancelInformationSourcePayload.Field()
    cancel_upload_task = CancelUploadTaskTask.Field()
    cancel_weak_supervision_task = CancelWeakSupervisionTask.Field()
    cancel_attribute_calculation_task = CancelAttributeCalculationTask.Field()
    cancel_tokenization_task = CancelTokenizationTask.Field()
    cancel_embedding_task = CancelEmbeddingTask.Field()
