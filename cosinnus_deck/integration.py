import logging

from django.contrib.auth import get_user_model
from requests.exceptions import ConnectionError, Timeout

from cosinnus.celery import app as celery_app
from cosinnus.core import signals
from cosinnus.integration import CosinnusBaseIntegrationHandler
from cosinnus.models.group import CosinnusGroup
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
from cosinnus.tasks import CeleryThreadTask
from cosinnus_deck.deck import DeckConnection, DeckConnectionException

logger = logging.getLogger(__name__)


# Singleton DeckIntegrationHandler instance ensuring that the hooks are initialized only once and allowing to call the
# handler functions directly.
DECK_SINGLETON = None


class DeckTask(CeleryThreadTask):
    """
    DeckApp synchronization task definition.
    Retry a task raising a requests error after: 15m, 30m, 1h, 2h, 4h, 8h, 16h, 24h, 24h, 24h.
    """

    autoretry_for = (
        ConnectionError,
        Timeout,
        DeckConnectionException,
    )
    max_retries = 10
    retry_backoff = 15 * 60  # 15m
    retry_backoff_max = 24 * 60 * 60  # 24h


class DeckIntegrationHandler(CosinnusBaseIntegrationHandler):
    """Deck integration."""

    # Enable group hooks.
    integrate_groups = True
    integrate_users = False
    integrate_oauth = False

    # Enable integration for Society and Project
    integrated_group_models = [CosinnusProject, CosinnusSociety]

    # Set fields relevant for integration
    integrated_instance_fields = {
        CosinnusProject: ['name'],
        CosinnusSociety: ['name'],
    }

    def __init__(self, *args, **kwargs):
        global DECK_SINGLETON
        if DECK_SINGLETON:
            # do not initialize hooks, if already initialized.
            return

        super().__init__(*args, **kwargs)

        # Deck creation is triggered after the nextcloud group has been initialized.
        signals.group_nextcloud_group_initialized.connect(self.do_group_nextcloud_group_initialized, weak=False)

        # set singleton instance
        DECK_SINGLETON = self

    """
    Group integration
    """

    def do_group_create(self, group):
        """
        Does nothing as the deck integration starts only after the nextcloud_group_id has been set.
        This is handled by the do_group_nextcloud_group_initialized hook.
        """
        pass

    def do_group_nextcloud_group_initialized(self, sender, group, **kwargs):
        """Create the Deck board."""
        if self._is_app_enabled_for_group(group):
            self._do_group_create.delay(group.pk)

    def do_group_update(self, group):
        """Group update handler."""
        if self._is_app_enabled_for_group(group) and group.nextcloud_deck_board_id:
            self._do_group_update.delay(group.pk)

    def do_group_delete(self, group):
        """Group delete handler."""
        if group.nextcloud_deck_board_id:
            self._do_group_board_delete.delay(group.nextcloud_deck_board_id)

    def do_group_activate(self, group):
        """Group (re-)activation handler."""
        if group.nextcloud_deck_board_id:
            self._do_group_update.delay(group.pk)

    def do_group_deactivate(self, group):
        """Group deactivation handler."""
        if group.nextcloud_deck_board_id:
            self._do_group_update.delay(group.pk)

    def do_group_app_activate(self, group):
        """Deck app has been activated in the group."""
        if group.nextcloud_deck_board_id:
            # Group board exists and will be reactivated by the update hook.
            self._do_group_update.delay(group.pk)
        elif group.nextcloud_group_id:
            # No group board, but nextcloud group initialized. Create the group board.
            self._do_group_create.delay(group.pk)

    def do_group_app_deactivate(self, group):
        """Deck app has been deactivated in the group."""
        if group.nextcloud_deck_board_id:
            self._do_group_update.delay(group.pk)

    def do_group_migrate_todo(self, group):
        """Migrate groups todos to deck."""
        self._do_group_migrate_todo.delay(group.pk)

    def do_migrate_user_decks(self, user, selected_decks):
        """Migrate user decks to group decks."""
        self._do_migrate_user_decks.delay(user.pk, selected_decks)

    """
    Celery tasks
    """

    @staticmethod
    @celery_app.task(base=DeckTask)
    def _do_group_create(group_id):
        """Create a Deck for a group."""
        group = CosinnusGroup.objects.filter(pk=group_id).first()
        if group and group.nextcloud_group_id and not group.nextcloud_deck_board_id:
            deck = DeckConnection()
            deck.group_board_create(group, initialize_board_content=True)

    @staticmethod
    @celery_app.task(base=DeckTask)
    def _do_group_update(group_id):
        """Update a Deck for a group considering the group and app active status."""
        group = CosinnusGroup.objects.filter(pk=group_id).first()
        if group and group.nextcloud_deck_board_id:
            deck = DeckConnection()
            deck.group_board_update(group)

    @staticmethod
    @celery_app.task(base=DeckTask)
    def _do_group_board_delete(group_board_id):
        """Delete a Deck for a group."""
        deck = DeckConnection()
        deck.group_board_delete(group_board_id)

    @staticmethod
    @celery_app.task(base=DeckTask)
    def _do_group_migrate_todo(group_id):
        """Migrate todos to the group board"""
        group = CosinnusGroup.objects.filter(pk=group_id).first()
        if group and not group.deck_todo_migration_in_progress():
            deck = DeckConnection()
            deck.group_migrate_todo(group)

    @staticmethod
    @celery_app.task(base=DeckTask)
    def _do_migrate_user_decks(user_id, selected_decks):
        """Migrate user decks to the group boards"""
        user = get_user_model().objects.filter(pk=user_id).first()
        if user and not user.cosinnus_profile.deck_migration_in_progress():
            deck = DeckConnection()
            deck.migrate_user_decks(user, selected_decks)
