# -*- coding: utf-8 -*-
from django.views.generic.base import TemplateView

from cosinnus.views.mixins.group import RequireReadMixin


class DeckView(RequireReadMixin, TemplateView):
    """Main deck app view containing a div used for the frontend app initialization."""

    # TODO: if the group does not have a deck-id try creating one, blocking

    template_name = 'cosinnus_deck/deck.html'


deck_view = DeckView.as_view()
