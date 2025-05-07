"""
Created on 05.08.2014

@author: Sascha
"""

from builtins import object

from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django_filters.filters import ChoiceFilter

from cosinnus.conf import settings
from cosinnus.forms.filters import (
    AllObjectsFilter,
    DropdownChoiceWidget,
    DropdownChoiceWidgetWithEmpty,
    SelectCreatorWidget,
)
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

    ONLINE_CHOICE = 'online'
    ON_SITE_CHOICE = 'onsite'
    online_or_onsite = ChoiceFilter(
        label=_('Online/On-Site'),
        choices=(
            (ONLINE_CHOICE, _('Online (has no location)')),
            (ON_SITE_CHOICE, _('On-Site (has location)')),
        ),
        widget=DropdownChoiceWidgetWithEmpty,
        method='filter_online_or_onsite',
    )

    hidden_filters = settings.COSINNUS_EVENT_EVENT_LIST_HIDDEN_FILTERS

    class Meta(object):
        model = Event
        fields = ['creator', 'o', 'online_or_onsite']

    def __init__(self, *args, **kwargs):
        # init hidden filters according to disabled features
        if (
            not settings.COSINNUS_EVENT_DIFFERENTIATE_ONLINE_AND_ONSITE_EVENTS
            and 'online_or_onsite' not in self.hidden_filters
        ):
            self.hidden_filters.append('online_or_onsite')
        super(EventFilter, self).__init__(*args, **kwargs)

    def filter_online_or_onsite(self, queryset, name, value):
        """Filter queryset by online (has no location) or on-site (has location).
        Note: Filtering non-proxy-events by media_tag location and proxy events by the group/conference location.
        """
        online_filter = (
            Q(is_hidden_group_proxy=False, media_tag__location__isnull=True)
            | Q(is_hidden_group_proxy=False, media_tag__location='')
            | Q(is_hidden_group_proxy=True, group__locations__location__isnull=True)
            | Q(is_hidden_group_proxy=True, group__locations__location='')
        )
        if value == self.ONLINE_CHOICE:
            queryset = queryset.filter(online_filter)
        elif value == self.ON_SITE_CHOICE:
            queryset = queryset.exclude(online_filter)
        return queryset
