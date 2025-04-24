import logging

from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_save

from cosinnus.celery import app as celery_app
from cosinnus.conf import settings
from cosinnus.integration import CosinnusBaseIntegrationHandler
from cosinnus.models import UserProfile
from cosinnus.models.conference import CosinnusConferenceRoom
from cosinnus.models.group import CosinnusGroup, CosinnusGroupMembership
from cosinnus.models.group_extra import CosinnusConference, CosinnusProject, CosinnusSociety
from cosinnus.tasks import CeleryThreadTask
from cosinnus_event.models import Event
from cosinnus_message.rocket_chat import (
    ROCKETCHAT_MESSAGE_ID_SETTINGS_KEY,
    RocketChatConnection,
    RocketChatDownException,
)
from cosinnus_note.models import Note

logger = logging.getLogger(__name__)


class RocketChatTask(CeleryThreadTask):
    """
    RocketChat synchronization task definition.
    Retry a task raising a RocketChatDownException after: 15m, 30m, 1h, 2h, 4h, 8h, 16h, 24h, 24h, 24h.
    """

    autoretry_for = (RocketChatDownException,)
    max_retries = 10
    retry_backoff = 15 * 60  # 15m
    retry_backoff_max = 24 * 60 * 60  # 24h


class RocketChatIntegrationHandler(CosinnusBaseIntegrationHandler):
    """RocketChat integration."""

    # Enable group, user and oauth hooks.
    integrate_groups = True
    integrate_users = True
    integrate_oauth = True

    # Enable integration for Society, Project and Conference
    # Note: Conference integration is disabled for new conferences in the respective hooks and tasks.
    integrated_group_models = [CosinnusProject, CosinnusSociety, CosinnusConference]

    # Set fields relevant for integration
    integrated_instance_fields = {
        CosinnusProject: ['name'],
        CosinnusSociety: ['name'],
        CosinnusConference: ['name'],
        get_user_model(): ['first_name', 'last_name', 'email'],
        UserProfile: ['email_verified', 'avatar'],
    }

    def __init__(self):
        super().__init__()

        # message relay hooks
        post_save.connect(self.do_relay_message_create_or_update, sender=Event, weak=False)
        post_delete.connect(self.do_relay_message_delete, sender=Event, weak=False)
        post_save.connect(self.do_relay_message_create_or_update, sender=Note, weak=False)
        post_delete.connect(self.do_relay_message_delete, sender=Note, weak=False)

        # conference room hooks
        post_delete.connect(self.do_conference_room_delete, sender=CosinnusConferenceRoom, weak=False)

    """
    User integration
    """

    def do_user_create(self, user):
        """
        User create handler.
        Note: User creation is blocking to avoid concurrency problem with subsequente profile update calls.
        """
        try:
            rocket = RocketChatConnection()
            rocket.users_create(user)
        except RocketChatDownException:
            logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
        except Exception as e:
            logger.exception(e)

    def do_user_update(self, user):
        """User update hook. Called for user or profile changes. Only update active users."""
        if user.is_active:
            self._do_user_update.delay(user.pk)

    def do_user_login(self, user):
        """User login handler. Checks if the user exists in rocketchat, and if not, attempts to create them."""
        self._do_user_sanity_check.delay(user.pk)

    def do_user_logout(self, user):
        """User logout hook. Triggered after a password change."""
        self._do_user_logout.delay(user.pk)

    def do_user_activate(self, user):
        """User (re-)activation handler."""
        self._do_user_activate.delay(user.pk)

    def do_user_deactivate(self, user):
        """User deactivation handler."""
        self._do_user_deactivate.delay(user.pk)

    def do_user_delete(self, user):
        """User delete handler."""
        try:
            rocket = RocketChatConnection()
            rocket.users_delete(user)
        except RocketChatDownException:
            logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
        except Exception as e:
            logger.exception(e)

    def do_user_promote_to_superuser(self, user):
        """User made superuser handler. Blocking, as called from the admin."""
        try:
            rocket = RocketChatConnection()
            rocket_user_id = rocket.get_user_id(user)
            if rocket_user_id:
                rocket.rocket.users_update(user_id=rocket_user_id, roles=['user', 'admin'])
        except RocketChatDownException:
            logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
        except Exception as e:
            logger.exception(e)

    def do_user_demote_from_superuser(self, user):
        """Superuser made user handler. Blocking, as called from the admin."""
        try:
            rocket = RocketChatConnection()
            rocket_user_id = rocket.get_user_id(user)
            if rocket_user_id:
                rocket.rocket.users_update(user_id=rocket_user_id, roles=['user'])
        except RocketChatDownException:
            logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
        except Exception as e:
            logger.exception(e)

    """
    User Celery tasks
    """

    @staticmethod
    @celery_app.task(base=RocketChatTask)
    def _do_user_update(user_id):
        """Update a user in RocketChat."""
        rocket = RocketChatConnection()
        user = get_user_model().objects.filter(pk=user_id).first()
        if user:
            rocket.users_update(user)

    @staticmethod
    @celery_app.task(base=RocketChatTask)
    def _do_user_sanity_check(user_id):
        """Ensure RocketChat user account sanity."""
        rocket = RocketChatConnection()
        user = get_user_model().objects.filter(pk=user_id).first()
        if user:
            rocket.ensure_user_account_sanity(user)

    @staticmethod
    @celery_app.task(base=RocketChatTask)
    def _do_user_logout(user_id):
        """Logout user from RocketChat."""
        rocket = RocketChatConnection()
        user = get_user_model().objects.filter(pk=user_id).first()
        if user:
            rocket.users_logout(user)

    @staticmethod
    @celery_app.task(base=RocketChatTask)
    def _do_user_activate(user_id):
        """(Re-)activate a user in RocketChat."""
        rocket = RocketChatConnection()
        user = get_user_model().objects.filter(pk=user_id).first()
        if user:
            rocket.users_enable(user)

    @staticmethod
    @celery_app.task(base=RocketChatTask)
    def _do_user_deactivate(user_id):
        """Deactivate a user in RocketChat."""
        rocket = RocketChatConnection()
        user = get_user_model().objects.filter(pk=user_id).first()
        if user:
            rocket.users_disable(user)

    """
    Group integration
    """

    def do_group_create(self, group):
        """Group create handler. Note: Conference channels are disabled for new conferences."""
        if not group.group_is_conference:
            self._do_group_create_or_update.delay(group.pk)

    def do_group_update(self, group):
        """Group update handler."""
        self._do_group_create_or_update.delay(group.pk)

    def do_group_delete(self, group):
        """Group delete handler."""
        for room_id in group.get_rocketchat_room_ids():
            self._do_group_room_delete.delay(room_id)

    def do_group_activate(self, group):
        """Group (re-)activation handler."""
        self._do_group_activate.delay(group.pk)

    def do_group_deactivate(self, group):
        """Group deactivation handler."""
        self._do_group_deactivate.delay(group.pk)

    def _membership_create_update_or_delete(self, membership):
        """Common handler for all membership changes."""
        self._do_membership_update.delay(membership.user.pk, membership.group.pk)
        if membership.group.group_is_conference:
            rocket_rooms = CosinnusConferenceRoom.objects.filter(
                group=membership.group, type__in=CosinnusConferenceRoom.ROCKETCHAT_ROOM_TYPES
            )
            # add/remove member from each rocketchat room for each conference room
            for room in rocket_rooms:
                self._do_conference_room_membership_update.delay(room.pk, membership.user.pk, membership.pk)

    def do_membership_create(self, membership):
        """Membership create handler."""
        self._membership_create_update_or_delete(membership)

    def do_membership_update(self, membership):
        """Membership update handler."""
        self._membership_create_update_or_delete(membership)

    def do_membership_delete(self, membership):
        """Membership delete handler."""
        self._membership_create_update_or_delete(membership)

    """
    Group Celery tasks
    """

    @staticmethod
    @celery_app.task(base=RocketChatTask)
    def _do_group_create_or_update(group_id):
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

    @staticmethod
    @celery_app.task(base=RocketChatTask)
    def _do_group_room_delete(room_id):
        """Delete a group room in RocketChat."""
        rocket = RocketChatConnection()
        rocket.groups_room_delete(room_id)

    @staticmethod
    def _get_group_specific_room_ids(rocket, group):
        """Return the room IDs for conference groups."""
        room_ids = None
        if group.group_is_conference:
            # Deactivate workshop rooms for conference groups.
            room_ids = [room.rocket_chat_room_id for room in group.rooms.all() if room.rocket_chat_room_name]
            # Deactivate default room, if exists.
            default_room_id = rocket.get_group_id(group, create_if_not_exists=False)
            if default_room_id:
                room_ids.append(default_room_id)
        return room_ids

    @staticmethod
    @celery_app.task(base=RocketChatTask)
    def _do_group_deactivate(group_id):
        """Archive group rooms in RocketChat."""
        rocket = RocketChatConnection()
        group = CosinnusGroup.objects.filter(pk=group_id).first()
        if group:
            specific_room_ids = RocketChatIntegrationHandler._get_group_specific_room_ids(rocket, group)
            rocket.groups_archive(group, specific_room_ids=specific_room_ids)

    @staticmethod
    @celery_app.task(base=RocketChatTask)
    def _do_group_activate(group_id):
        """Unarchive group rooms in RocketChat."""
        rocket = RocketChatConnection()
        group = CosinnusGroup.objects.filter(pk=group_id).first()
        if group:
            specific_room_ids = RocketChatIntegrationHandler._get_group_specific_room_ids(rocket, group)
            rocket.groups_unarchive(group, specific_room_ids=specific_room_ids)

    @staticmethod
    @celery_app.task(base=RocketChatTask)
    def _do_membership_update(user_id, group_id):
        """Create, update or delete the group membership for group rooms in RocketChat."""

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

    @staticmethod
    @celery_app.task(base=RocketChatTask)
    def _do_conference_room_membership_update(room_id, user_id, group_id):
        """Update the user membership for a conference room channel in RocketChat."""
        rocket = RocketChatConnection()
        room = CosinnusConferenceRoom.objects.get(pk=room_id)
        user = get_user_model().objects.filter(pk=user_id).first()
        if room and user:
            # In case the room channel was not created because of an error, recreate it.
            room.sync_rocketchat_room()
            if room.rocket_chat_room_id:
                membership = CosinnusGroupMembership.objects.filter(user_id=user_id, group_id=group_id).first()
                if membership:
                    # membership created or updated
                    rocket.invite_or_kick_for_room_membership(membership, room.rocket_chat_room_id)
                else:
                    # membership deleted
                    rocket.remove_member_from_room(user, room.rocket_chat_room_id)

    """
    OAuth hook
    """

    def check_oauth_application_matches(self, application_name):
        """Returns True if the application name matches the integrated service."""
        return application_name.startswith('rocketchat')

    def do_oauth_app_authorize(self, token):
        """OAuth authorization handler. Makes sure that the RC user account is created and up to date."""
        rocket = RocketChatConnection()
        rocket.users_create_or_update(token.user)

    """
    Custom Conference Hooks
    Note: The channel creation is done directly in cosinnus_conference.api.serializers.py via get_rocketchat_room_url.
    """

    def do_conference_room_delete(self, sender, instance, **kwargs):
        if instance.rocket_chat_room_id:
            self._do_group_room_delete(instance.rocket_chat_room_id)

    """
    Custom message relay
    """

    def do_relay_message_create_or_update(self, sender, instance, created, **kwargs):
        """Hooks to create or update a relayed message."""
        if created:
            self._do_relay_message_create.delay(instance._meta.model_name, instance.pk)
        else:
            self._do_relay_message_update.delay(instance._meta.model_name, instance.pk)

    def do_relay_message_delete(self, sender, instance, **kwargs):
        """Hook to delete a relay message."""
        if hasattr(instance, 'is_hidden_group_proxy') and instance.is_hidden_group_proxy:
            # Conference proxy events are not relayed.
            return
        room_key = settings.COSINNUS_ROCKET_NOTE_POST_RELAY_ROOM_KEY
        msg_id = instance.settings.get(ROCKETCHAT_MESSAGE_ID_SETTINGS_KEY)
        if room_key and msg_id:
            self._do_relay_message_delete(instance.group.pk, room_key, msg_id)

    @staticmethod
    def _get_relay_message_instance(model_name, instance_id):
        """Helper to get the instance for a relay message by model-name and id."""
        model = None
        if model_name == 'note':
            model = Note
        elif model_name == 'event':
            model = Event
        instance = model.objects.filter(pk=instance_id).first()
        return instance

    @staticmethod
    @celery_app.task(base=RocketChatTask)
    def _do_relay_message_create(model_name, instance_id):
        """Create a relayed message in RocketChat."""
        instance = RocketChatIntegrationHandler._get_relay_message_instance(model_name, instance_id)
        if instance:
            rocket = RocketChatConnection()
            rocket.relay_message_create(instance)

    @staticmethod
    @celery_app.task(base=RocketChatTask)
    def _do_relay_message_update(model_name, instance_id):
        """Update a relayed massage in RocketChat."""
        instance = RocketChatIntegrationHandler._get_relay_message_instance(model_name, instance_id)
        if instance:
            rocket = RocketChatConnection()
            rocket.relay_message_update(instance)

    @staticmethod
    @celery_app.task(base=RocketChatTask)
    def _do_relay_message_delete(group_id, room_key, msg_id):
        """Delete a relayed message in RocketChat."""
        rocket = RocketChatConnection()
        group = CosinnusGroup.objects.filter(pk=group_id).first()
        if group:
            rocket.relay_message_delete_in_group(group, room_key, msg_id)
