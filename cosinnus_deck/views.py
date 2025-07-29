import json

from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView, View

from cosinnus.models.group import CosinnusGroup, CosinnusPortal
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.permissions import check_ug_admin
from cosinnus.views.mixins.group import RequireLoggedInMixin, RequireReadMixin, RequireWriteGrouplessMixin
from cosinnus_todo.models import TodoEntry


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


class DeckMigrateTodoView(RequireWriteGrouplessMixin, TemplateView):
    """
    Allows users to migrate cosinnus_todo lists and tasks to the group board.
    Note: Implemented as groupless view as the deck app might be disabled in the beginning.
    """

    template_name = 'cosinnus_deck/deck_migrate_todo.html'
    group = None

    def dispatch(self, request, *args, **kwargs):
        group_slug = kwargs.get('group')
        self.group = get_object_or_404(
            get_cosinnus_group_model(), slug=group_slug, portal_id=CosinnusPortal.get_current().id
        )
        return super(DeckMigrateTodoView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if self.group.deck_todo_migration_allowed():
            # start the migration task
            from cosinnus_deck.integration import DECK_SINGLETON

            self.group.deck_todo_migration_set_status(self.group.DECK_TODO_MIGRATION_STATUS_STARTED)
            DECK_SINGLETON.do_group_migrate_todo(self.group)
        return self.get(request, *args, **kwargs)

    def get_object(self, *args, **kwargs):
        return self.group

    def get_context_data(self, **kwargs):
        context = super(DeckMigrateTodoView, self).get_context_data(**kwargs)
        migration_required = TodoEntry.objects.filter(todolist__group=self.group, media_tag__migrated=False).exists()
        context.update(
            {
                'group': self.group,
                'deck_migrated_required': migration_required,
                'deck_migration_status': self.group.deck_todo_migration_status(),
            }
        )

        return context


deck_migrate_todo_view = DeckMigrateTodoView.as_view()


class DeckMigrateUserDecksView(RequireLoggedInMixin, TemplateView):
    template_name = 'cosinnus_deck/deck_migrate_user_decks.html'

    def get_context_data(self, **kwargs):
        context = super(DeckMigrateUserDecksView, self).get_context_data(**kwargs)
        user_admin_groups = [
            [group.pk, group.name]
            for group in CosinnusGroup.objects.get_for_user_group_admin(self.request.user)
            if group.type in [CosinnusGroup.TYPE_PROJECT, CosinnusGroup.TYPE_SOCIETY]
        ]
        context['user_admin_groups'] = json.dumps(user_admin_groups)
        context['migration_in_progress'] = self.request.user.cosinnus_profile.deck_migration_in_progress()
        return context


deck_migrate_user_decks_view = DeckMigrateUserDecksView.as_view()


class DeckMigrateUserDecksApiView(RequireLoggedInMixin, View):
    def post(self, request, *args, **kwargs):
        user = request.user
        migration_data = json.loads(request.body)
        admin_group_ids = list(CosinnusGroup.objects.get_for_user_group_admin_pks(user))
        # check group permissions
        for board_data in migration_data:
            group_id = board_data['group']
            if group_id not in admin_group_ids:
                return HttpResponse(status=403)
        profile = user.cosinnus_profile
        if profile.deck_migration_allowed():
            # start the migration task
            from cosinnus_deck.integration import DECK_SINGLETON

            profile.deck_migration_set_status(profile.DECK_MIGRATION_STATUS_STARTED)
            DECK_SINGLETON.do_migrate_user_decks(user, migration_data)
        return HttpResponse(status=200)

    def get(self, request, *args, **kwargs):
        status = request.user.cosinnus_profile.deck_migration_status()
        data = {'status': status}
        return JsonResponse(data=data)


deck_migrate_user_decks_api_view = DeckMigrateUserDecksApiView.as_view()
