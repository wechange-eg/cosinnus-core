import json
import logging

from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView, View

from cosinnus.models.group import CosinnusGroup
from cosinnus.utils.permissions import check_ug_admin
from cosinnus.views.mixins.group import RequireLoggedInMixin, RequireReadMixin, RequireWriteMixin
from cosinnus_todo.models import TodoEntry

logger = logging.getLogger(__name__)


class DeckView(RequireReadMixin, TemplateView):
    """Main deck app view containing a div used for the frontend app initialization."""

    template_name = 'cosinnus_deck/deck.html'

    def get(self, request, *args, **kwargs):
        if not self.group.nextcloud_deck_board_id and check_ug_admin(request.user, self.group):
            # add admin warning
            message = _(
                'If the task-board is not available withing a few minutes, some technical difficulties occurred with '
                'the board service. Try disabling and re-enabling the task-board app in the settings. '
                'If the problems persist, please contact the support. We apologize for the inconveniences!'
            )
            messages.warning(self.request, message)
        return super(DeckView, self).get(request, *args, **kwargs)


deck_view = DeckView.as_view()


class DeckMigrateTodoView(RequireWriteMixin, TemplateView):
    """Allows users to migrate cosinnus_todo lists and tasks to the group board."""

    template_name = 'cosinnus_deck/deck_migrate_todo.html'
    # the view can be accessed before the deck app is activated
    ALLOW_VIEW_ACCESS_WHEN_GROUP_APP_DEACTIVATED = True

    def post(self, request, *args, **kwargs):
        if self.group.deck_migration_allowed():
            # start the migration task
            self.group.deck_migration_set_status(self.group.DECK_MIGRATION_STATUS_STARTED)
            try:
                from cosinnus_deck.integration import DECK_SINGLETON

                DECK_SINGLETON.do_group_migrate_todo(self.group)
            except Exception as e:
                self.group.deck_migration_set_status(self.group.DECK_MIGRATION_STATUS_FAILED)
                logger.exception(e)
        return self.get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DeckMigrateTodoView, self).get_context_data(**kwargs)
        migration_required = TodoEntry.objects.filter(todolist__group=self.group, media_tag__migrated=False).exists()
        context.update(
            {
                'deck_migrated_required': migration_required,
                'deck_migration_status': self.group.deck_migration_status(),
            }
        )
        return context


deck_migrate_todo_view = DeckMigrateTodoView.as_view()


class DeckMigrateUserDecksView(RequireLoggedInMixin, TemplateView):
    """
    View providing the user deck migration page.
    The page uses js to fetch the user boards from NextCloud and offers a group selection for the migration. Only
    groups where the user is admin a shown.
    When the migration is started the js code shares the board with the admin user in NextCloud, if needed. Then it
    triggers the backend migration with a post to DeckMigrateUserDecksApiView. While the migration  is in progress the
    migration status is updated from that view.
    """

    template_name = 'cosinnus_deck/deck_migrate_user_decks.html'

    def get_context_data(self, **kwargs):
        context = super(DeckMigrateUserDecksView, self).get_context_data(**kwargs)
        # get groups where the user is admin, used to select the migration target
        user_admin_groups = [
            [group.pk, group.name]
            for group in CosinnusGroup.objects.get_for_user_group_admin(self.request.user)
            if group.type in [CosinnusGroup.TYPE_PROJECT, CosinnusGroup.TYPE_SOCIETY]
        ]
        context['user_admin_groups'] = json.dumps(user_admin_groups)
        # add current migration status to context
        context['migration_in_progress'] = self.request.user.cosinnus_profile.deck_migration_in_progress()
        return context


deck_migrate_user_decks_view = DeckMigrateUserDecksView.as_view()


class DeckMigrateUserDecksApiView(RequireLoggedInMixin, View):
    """API used by the DeckMigrateUserDecksView js code to start the backend migration and get the current status."""

    def post(self, request, *args, **kwargs):
        """Start the migration task in the backend for the selected boards and groups."""
        user = request.user
        migration_data = json.loads(request.body)

        # validate migration data
        try:
            assert isinstance(migration_data, list)
            for board_data in migration_data:
                assert 'board' in board_data
                assert isinstance(board_data['board'], int)
                assert 'group' in board_data
                assert isinstance(board_data['group'], int)
        except AssertionError as e:
            logger.warning('Migrate User Deck API: Invalid request!', extra={'exception': e})
            return HttpResponse(status=400)

        # check group permissions
        admin_group_ids = list(CosinnusGroup.objects.get_for_user_group_admin_pks(user))
        for board_data in migration_data:
            group_id = board_data['group']
            if group_id not in admin_group_ids:
                return HttpResponse(status=403)

        profile = user.cosinnus_profile
        if profile.deck_migration_allowed():
            # start the migration task
            profile.deck_migration_set_status(profile.DECK_MIGRATION_STATUS_STARTED)
            try:
                from cosinnus_deck.integration import DECK_SINGLETON

                DECK_SINGLETON.do_migrate_user_decks(user, migration_data)
            except Exception as e:
                profile.deck_migration_set_status(profile.DECK_MIGRATION_STATUS_FAILED)
                logger.exception(e)
        return HttpResponse(status=200)

    def get(self, request, *args, **kwargs):
        """Get the current migration status to show the user the respective info."""
        status = request.user.cosinnus_profile.deck_migration_status()
        data = {'status': status}
        return JsonResponse(data=data)


deck_migrate_user_decks_api_view = DeckMigrateUserDecksApiView.as_view()
