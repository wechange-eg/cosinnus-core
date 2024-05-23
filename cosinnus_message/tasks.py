# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model

from cosinnus.celery import app as celery_app
from cosinnus.models.group import CosinnusGroup, CosinnusGroupMembership
from cosinnus.tasks import CeleryThreadTask
from cosinnus_message.rocket_chat import RocketChatConnection, RocketChatDownException


class RocketChatTask(CeleryThreadTask):
    """
    RocketChat synchronization task definition.
    Retry a task raising a RocketChatDownException after: 15m, 30m, 1h, 2h, 4h, 8h, 16h, 24h, 24h, 24h.
    """

    autoretry_for = (RocketChatDownException,)
    max_retries = 10
    retry_backoff = 15 * 60  # 15m
    retry_backoff_max = 24 * 60 * 60  # 24h


def _group_is_conference_without_default_channel(rocket, group):
    """
    Helper to check if group is a conference without a default channel. We disabled default channel creation for
    conferences but still need to handle conferences created before this that still have a default channel.
    """
    if group.group_is_conference:
        default_room_id = rocket.get_group_id(group, create_if_not_exists=False)
        if not default_room_id:
            return True
    return False


@celery_app.task(base=RocketChatTask)
def rocket_group_membership_update_task(user_id, group_id):
    """Updates RocketChat default channel member status for a group membership."""
    rocket = RocketChatConnection()
    membership = CosinnusGroupMembership.objects.filter(user_id=user_id, group_id=group_id).first()
    if membership:
        # update existing membership

        # Check if a default channel exists for a conference. If not there is nothing to be done.
        if _group_is_conference_without_default_channel(rocket, membership.group):
            return

        rocket.invite_or_kick_for_membership(membership)
    else:
        # membership deleted
        user = get_user_model().objects.filter(pk=user_id).first()
        group = CosinnusGroup.objects.filter(pk=group_id).first()

        if user and group:
            # Check if a default channel exists for a conference. If not there is nothing to be done.
            if _group_is_conference_without_default_channel(rocket, group):
                return

            rocket.groups_kick(user, group)
