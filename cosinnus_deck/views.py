from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView

from cosinnus.utils.permissions import check_ug_admin
from cosinnus.views.mixins.group import RequireReadMixin


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
