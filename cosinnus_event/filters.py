"""
Created on 05.08.2014

@author: Sascha
"""

from builtins import object

from django.utils.translation import gettext_lazy as _

from cosinnus.conf import settings
from cosinnus.forms.filters import AllObjectsFilter, DropdownChoiceWidget, SelectCreatorWidget
from cosinnus.views.mixins.filters import CosinnusFilterSet, CosinnusOrderingFilter
from cosinnus_event.models import Event


class EventFilter(CosinnusFilterSet):
    creator = AllObjectsFilter(label=_('Created By'), widget=SelectCreatorWidget)

    o = CosinnusOrderingFilter(
        fields=(
            ('from_date', 'from_date'),
            ('created', 'created'),
            ('title', 'title'),
        ),
        choices=(
            ('-from_date', _('Soonest Upcoming')),
            ('-created', _('Newest Created')),
            ('title', _('Title')),
        ),
        default='-from_date',
        widget=DropdownChoiceWidget,
    )

    hidden_filters = settings.COSINNUS_EVENT_EVENT_LIST_HIDDEN_FILTERS

    class Meta(object):
        model = Event
        fields = ['creator', 'o']
