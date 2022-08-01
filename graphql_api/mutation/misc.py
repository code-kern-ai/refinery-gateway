from typing import Any, Dict
from util import doc_ock, notification

import graphene
from controller.misc import manager
from submodules.model.business_objects import organization
from controller.auth import manager as auth
from submodules.model.events import *


class UpdateConfig(graphene.Mutation):
    class Arguments:
        dict_str = graphene.String(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, dict_str: str):
        auth.check_demo_access(info)
        if manager.check_is_managed():
            print(
                "config should only be changed for open source/local version to prevent limit issues"
            )
        manager.update_config(dict_str)
        manager.refresh_config()
        orgs = organization.get_all()
        if not orgs or len(orgs) != 1:
            print("local version should only have one organization")

        for org in orgs:
            # send to all so all are notified about the change
            notification.send_organization_update(
                None, f"config_updated", True, str(org.id)
            )
        return UpdateConfig(ok=True)


class PostDocOck(graphene.Mutation):
    class Arguments:
        event_name = graphene.String(required=True)
        event_data = graphene.JSONString(required=True)

    ok = graphene.Boolean()

    def mutate(self, info, event_name: str, event_data: Dict[str, Any]):
        auth.check_demo_access(info)
        user = auth.get_user_by_info(info)
        event = globals()[event_name]
        event_instance = event(**event_data)

        for key in event_data:
            setattr(event_instance, key, event_data[key])
        doc_ock.post_event(user, event_instance)
        return UpdateConfig(ok=True)


class MiscMutation(graphene.ObjectType):
    update_config = UpdateConfig.Field()
    post_event = PostDocOck.Field()
