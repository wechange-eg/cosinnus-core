from django.db.models import Q
from django.utils.timezone import now
from rest_framework import viewsets

from cosinnus.api.views.mixins import CosinnusFilterQuerySetMixin, PublicTaggableObjectFilterMixin
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus_event.api.serializers import EventListSerializer, EventRetrieveSerializer
from cosinnus_event.models import Event


class ScheduledFilterMixin(object):
    def get_queryset(self):
        queryset = super().get_queryset()
        # filter scheduled events
        queryset = queryset.filter(state=Event.STATE_SCHEDULED).exclude(is_hidden_group_proxy=True)
        # exclude conference workshops
        conference_type = get_cosinnus_group_model().TYPE_CONFERENCE
        queryset = queryset.exclude(group__type=conference_type)
        return queryset


class EventViewSet(
    ScheduledFilterMixin, CosinnusFilterQuerySetMixin, PublicTaggableObjectFilterMixin, viewsets.ReadOnlyModelViewSet
):
    queryset = Event.objects.all()
    FILTER_CONDITION_MAP = {'upcoming': {'true': [Q(to_date__gte=now())]}}
    FILTER_DEFAULT_ORDER = [
        'from_date',
    ]
    MANAGED_TAGS_FILTER_ON_GROUP = True

    def get_serializer_class(self):
        if self.action == 'list':
            return EventListSerializer
        if self.action == 'retrieve':
            return EventRetrieveSerializer
        return EventRetrieveSerializer
