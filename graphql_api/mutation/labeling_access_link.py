from controller.auth import manager as auth
import graphene
from submodules.model import enums
from controller.labeling_access_link import manager
from graphql_api.types import LabelingAccessLink
from util import notification


class GenerateAccessLink(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        type = graphene.String(required=True)
        id = graphene.ID(required=True)

    # id = graphene.ID()
    link = graphene.Field(LabelingAccessLink)

    def mutate(
        self,
        info,
        project_id: str,
        type: str,
        id: str,
    ):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        user = auth.get_user_by_info(info)
        try:
            link_type_parsed = enums.LinkTypes[type.upper()]
        except KeyError:
            raise ValueError(f"Invalid LinkTypes: {type}")

        if link_type_parsed == enums.LinkTypes.HEURISTIC:
            link = manager.generate_heuristic_access_link(project_id, user.id, id)
        elif link_type_parsed == enums.LinkTypes.DATA_SLICE:
            print("not yet supported")
        notification.send_organization_update(
            project_id, f"access_link_created:{str(link.id)}"
        )
        return GenerateAccessLink(link=link)


class RemoveAccessLink(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        link_id = graphene.ID(required=True)

    # id = graphene.ID()
    ok = graphene.Boolean()

    def mutate(
        self,
        info,
        project_id: str,
        link_id: str,
    ):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        type_id = manager.remove(link_id)
        notification.send_organization_update(
            project_id, f"access_link_removed:{link_id}:{type_id}"
        )
        return RemoveAccessLink(ok=True)


class LockAccessLink(graphene.Mutation):
    class Arguments:
        project_id = graphene.ID(required=True)
        link_id = graphene.ID(required=True)
        lock_state = graphene.Boolean(required=False)

    ok = graphene.Boolean()

    def mutate(
        self,
        info,
        project_id: str,
        link_id: str,
        lock_state: bool = True,
    ):
        auth.check_demo_access(info)
        auth.check_project_access(info, project_id)
        type_id = manager.change_user_access_to_link_lock(link_id, lock_state)
        notification.send_organization_update(
            project_id, f"access_link_changed:{link_id}:{type_id}:{lock_state}"
        )
        return LockAccessLink(ok=True)


class LabelingAccessLinkMutation(graphene.ObjectType):
    generate_access_link = GenerateAccessLink.Field()
    remove_access_link = RemoveAccessLink.Field()
    lock_access_link = LockAccessLink.Field()
