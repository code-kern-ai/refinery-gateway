from typing import Any, Dict
from controller.auth import manager as auth
from controller.embedding import manager
from controller.auth.manager import get_user_by_info
from util import notification
import graphene

from controller.task_queue import manager as task_queue_manager
from submodules.model.enums import TaskType
from submodules.model.business_objects import attribute as attribute_do


class CreateEmbedding(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        attribute_id = graphene.ID(required=True)
        config = graphene.JSONString()

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, attribute_id: str, config: Dict[str, Any]):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = get_user_by_info(info)

        embedding_type = config[
            "embeddingType"
        ]  # should raise an exception if not present
        platform = config.get("platform")
        model = config.get("model")
        api_token = config.get("apiToken")
        terms_text = config.get("termsText")
        terms_accepted = config.get("termsAccepted")
        additional_data = {
            "base": config.get("base"),
            "type": config.get("type"),
            "version": config.get("version"),
        }

        # prototyping logic, this will be part of config after ui integration
        relevant_attribute_list = attribute_do.get_all_possible_names_for_qdrant(
            project_id
        )

        task_queue_manager.add_task(
            project_id,
            TaskType.EMBEDDING,
            user.id,
            {
                "embedding_type": embedding_type,
                "attribute_id": attribute_id,
                "embedding_name": manager.get_embedding_name(
                    project_id, attribute_id, platform, embedding_type, model, api_token
                ),
                "platform": platform,
                "model": model,
                "api_token": api_token,
                "terms_text": terms_text,
                "terms_accepted": terms_accepted,
                "filter_attributes": relevant_attribute_list,
                "additional_data": additional_data,
            },
        )
        notification.send_organization_update(
            project_id=project_id, message="embedding:queued"
        )
        return CreateEmbedding(ok=True)


class DeleteEmbedding(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        embedding_id = graphene.ID(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, project_id: str, embedding_id: str):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        manager.delete_embedding(project_id, embedding_id)
        notification.send_organization_update(
            project_id, f"embedding_deleted:{embedding_id}"
        )
        return DeleteEmbedding(ok=True)


class EmbeddingMutation(graphene.ObjectType):
    create_embedding = CreateEmbedding.Field()
    delete_embedding = DeleteEmbedding.Field()
