import logging

from requests.exceptions import ConnectionError, Timeout

from cosinnus.celery import app as celery_app
from cosinnus.integration import CosinnusBaseIntegrationHandler
from cosinnus.models.group import CosinnusGroup
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
from cosinnus.tasks import CeleryThreadTask
from cosinnus_deck.deck import DeckConnection

logger = logging.getLogger(__name__)


# Singleton DeckIntegrationHandler instance ensuring that the hooks are initialized only once and allowing to call the
# handler functions directly.
DECK_SINGLETON = None


class DeckTask(CeleryThreadTask):
    """
    DeckApp synchronization task definition.
    Retry a task raising a requests error after: 15m, 30m, 1h, 2h, 4h, 8h, 16h, 24h, 24h, 24h.
    """

    autoretry_for = (ConnectionError, Timeout)
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
        CosinnusProject: ['name', 'nextcloud_group_id'],
        CosinnusSociety: ['name', 'nextcloud_group_id'],
    }

    def __init__(self):
        global DECK_SINGLETON
        if DECK_SINGLETON:
            # do not initialize hooks, if already initialized.
            return

        super().__init__()

        # set singleton instance
        DECK_SINGLETON = self

    """
    Group integration
    """

    def do_group_create(self, group):
        """Does nothing as the deck integration starts only after the nextcloud_group_id has been set."""
        pass

    def do_group_update(self, group):
        """Group update handler."""
        self._do_group_create_or_update.delay(group.pk)

    def do_group_delete(self, group):
        """Group delete handler."""
        pass

    def do_group_activate(self, group):
        """Group (re-)activation handler."""
        pass

    def do_group_deactivate(self, group):
        """Group deactivation handler."""
        pass

    """
    Group Celery tasks
    """

    @staticmethod
    @celery_app.task(base=DeckTask)
    def _do_group_create_or_update(group_id):
        """Create or update a Deck for a group."""
        group = CosinnusGroup.objects.filter(pk=group_id).first()
        if group and group.nextcloud_group_id:
            deck = DeckConnection()
            if not group.nextcloud_deck_board_id:
                # create group board
                board_id = deck.board_create(group.name)
                deck.board_add_group_access(board_id, group.nextcloud_group_id)
                type(group).objects.filter(pk=group.pk).update(nextcloud_deck_board_id=board_id)
            else:
                # update board name
                deck.board_update(group.nextcloud_deck_board_id, group.name)
