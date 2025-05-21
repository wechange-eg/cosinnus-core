from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView

from cosinnus.views.mixins.group import RequireReadMixin
from cosinnus_deck.deck import DeckConnection


class DeckView(RequireReadMixin, TemplateView):
    """Main deck app view containing a div used for the frontend app initialization."""

    template_name = 'cosinnus_deck/deck.html'

    def get(self, request, *args, **kwargs):
        if not self.group.nextcloud_deck_board_id and self.group.nextcloud_group_id:
            # Deck board not initialized via hooks, try initializing it now.
            try:
                deck = DeckConnection()
                deck.group_board_create(self.group)
            except Exception:
                pass  # the error is logged in the conneciton.
        if not self.group.nextcloud_deck_board_id:
            # add error message
            error_message = _(
                'We are currently experiencing some technical difficulties with the Deck service. '
                'Please try again later. We apologize for the inconveniences!'
            )
            messages.error(self.request, error_message)
        return super(DeckView, self).get(request, *args, **kwargs)


deck_view = DeckView.as_view()
