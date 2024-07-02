# -*- coding: utf-8 -*-
from django.contrib.auth import get_user_model

from cosinnus.celery import app as celery_app
from cosinnus.models.group import CosinnusGroup, CosinnusGroupMembership
from cosinnus.tasks import CeleryThreadTask
from cosinnus_event.models import Event
from cosinnus_message.rocket_chat import RocketChatConnection, RocketChatDownException
from cosinnus_note.models import Note


class RocketChatTask(CeleryThreadTask):
    """
    RocketChat synchronization task definition.
    Retry a task raising a RocketChatDownException after: 15m, 30m, 1h, 2h, 4h, 8h, 16h, 24h, 24h, 24h.
    """

    autoretry_for = (RocketChatDownException,)
    max_retries = 10
    retry_backoff = 15 * 60  # 15m
    retry_backoff_max = 24 * 60 * 60  # 24h


@celery_app.task(base=RocketChatTask)
def rocket_user_update_task(user_id, force_update, update_password):
    """Update a user in RocketChat."""
    rocket = RocketChatConnection()
    user = get_user_model().objects.filter(pk=user_id).first()
    if user:
        rocket.users_update(user, force_user_update=force_update, update_password=update_password)


@celery_app.task(base=RocketChatTask)
def rocket_user_deactivate_task(user_id):
    """Deactivate a user in RocketChat."""
    rocket = RocketChatConnection()
    user = get_user_model().objects.filter(pk=user_id).first()
    if user:
        rocket.users_disable(user)


@celery_app.task(base=RocketChatTask)
def rocket_user_reactivate_task(user_id):
    """Reactivate a user in RocketChat."""
    rocket = RocketChatConnection()
    user = get_user_model().objects.filter(pk=user_id).first()
    if user:
        rocket.users_enable(user)


@celery_app.task(base=RocketChatTask)
def rocket_user_sanity_task(user_id):
    """Ensure RocketChat user account sanity."""
    rocket = RocketChatConnection()
    user = get_user_model().objects.filter(pk=user_id).first()
    if user:
        rocket.ensure_user_account_sanity(user)


@celery_app.task(base=RocketChatTask)
def rocket_group_update_task(group_id):
    """Create or update a RocketChat channels for a group."""
    rocket = RocketChatConnection()
    group = CosinnusGroup.objects.filter(pk=group_id).first()
    if group:
        if group.group_is_group or group.group_is_project:
            # Channels are created only for groups and projects.
            if rocket.get_group_id(group, create_if_not_exists=False):
                # update existing group
                if rocket.groups_names_changed(group):
                    # update group name
                    rocket.groups_rename(group)
            else:
                # create group
                rocket.groups_create(group)


@celery_app.task(base=RocketChatTask)
def rocket_group_archive_task(group_id):
    """Archive a group."""
    rocket = RocketChatConnection()
    group = CosinnusGroup.objects.filter(pk=group_id).first()
    if group:
        specific_room_ids = None
        if group.group_is_conference:
            # Deactivate workshop rooms for conference groups.
            specific_room_ids = [room.rocket_chat_room_id for room in group.rooms.all() if room.rocket_chat_room_name]
            # Deactivate default room, if exists.
            default_room_id = rocket.get_group_id(group, create_if_not_exists=False)
            if default_room_id:
                specific_room_ids.append(default_room_id)
        rocket.groups_archive(group, specific_room_ids=specific_room_ids)


@celery_app.task(base=RocketChatTask)
def rocket_group_unarchive_task(group_id):
    """Unarchive a group."""
    rocket = RocketChatConnection()
    group = CosinnusGroup.objects.filter(pk=group_id).first()
    if group:
        specific_room_ids = None
        if group.group_is_conference:
            # Reactivate workshop rooms for conferences.
            specific_room_ids = [room.rocket_chat_room_id for room in group.rooms.all() if room.rocket_chat_room_name]
            # Deactivate default room, if exists.
            default_room_id = rocket.get_group_id(group, create_if_not_exists=False)
            if default_room_id:
                specific_room_ids.append(default_room_id)
        rocket.groups_unarchive(group, specific_room_ids=specific_room_ids)


@celery_app.task(base=RocketChatTask)
def rocket_group_room_delete_task(room_id):
    """Delete a group room."""
    rocket = RocketChatConnection()
    rocket.groups_room_delete(room_id)


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
    """Update the RocketChat default channel member status for a group membership."""
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


def _get_relay_message_instance(model_name, instance_id):
    """Helper to get the instance for a relay message by model-name and id."""
    model = None
    if model_name == 'note':
        model = Note
    elif model_name == 'event':
        model = Event
    instance = model.objects.filter(pk=instance_id).first()
    return instance


@celery_app.task(base=RocketChatTask)
def rocket_relay_message_create_task(model_name, instance_id):
    """Create a relayed message."""
    instance = _get_relay_message_instance(model_name, instance_id)
    if instance:
        rocket = RocketChatConnection()
        rocket.relay_message_create(instance)


@celery_app.task(base=RocketChatTask)
def rocket_relay_message_update_task(model_name, instance_id):
    """Update a relayed massage."""
    instance = _get_relay_message_instance(model_name, instance_id)
    if instance:
        rocket = RocketChatConnection()
        rocket.relay_message_update(instance)


@celery_app.task(base=RocketChatTask)
def rocket_relay_message_delete_task(group_id, room_key, msg_id):
    """Delete a relayed message."""
    rocket = RocketChatConnection()
    group = CosinnusGroup.objects.filter(pk=group_id).first()
    if group:
        rocket.relay_message_delete_in_group(group, room_key, msg_id)
