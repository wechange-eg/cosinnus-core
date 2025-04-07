from django.db.models import Count, Q
from django.utils.timezone import now
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets

from cosinnus.api.views.mixins import CosinnusFilterQuerySetMixin, PublicTaggableObjectFilterMixin
from cosinnus.models import MEMBER_STATUS
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
    """
    An endpoint that returns publicly visible events.
    """

    queryset = Event.objects.all()
    FILTER_CONDITION_MAP = {'upcoming': {'true': [Q(to_date__gte=now())]}}
    FILTER_DEFAULT_ORDER = [
        'from_date',
    ]
    MANAGED_TAGS_FILTER_ON_GROUP = True

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'group_id',
                openapi.IN_QUERY,
                description='If provided, will only return items belonging to the group/project with the given '
                'group id. Group ids are displayed in the `/groups/` and `/projects/` endpoints.',
                type=openapi.TYPE_INTEGER,
            ),
        ],
    )
    def list(self, request, **kwargs):
        return super().list(request, **kwargs)

    def get_serializer_class(self):
        if self.action == 'list':
            return EventListSerializer
        if self.action == 'retrieve':
            return EventRetrieveSerializer
        return EventRetrieveSerializer


class EventExchangeViewSet(EventViewSet):
    """Adds an additional filter that excludes groups/projects with only one member,
    for use with `CosinnusFilterQuerySetMixin`.
    TODO: this needs further optimization/debugging, as it does not scale at all with 100k Event items in DB!"""

    def _expensive_exclude_single_member_groups(self, qs):
        """This will also ignore any inactive users as group members, but is very DB-heavy."""
        qs = qs.annotate(
            count_group_members=Count(
                'group__memberships',
                filter=Q(
                    group__memberships__status__in=MEMBER_STATUS,
                    group__memberships__user__is_active=True,
                    group__memberships__user__cosinnus_profile__tos_accepted=True,
                )
                & ~Q(
                    group__memberships__user__last_login__exact=None,
                    group__memberships__user__email__icontains='__unverified__',
                    group__memberships__user__cosinnus_profile___is_guest=True,
                ),
            )
        ).filter(count_group_members__gt=1)
        return qs

    def _still_expensive_exclude_single_member_groups(self, qs):
        qs = qs.annotate(
            count_group_members=Count('group__memberships', filter=Q(group__memberships__status__in=MEMBER_STATUS))
        ).filter(count_group_members__gt=1)
        return qs

    additional_qs_filter_func = None
