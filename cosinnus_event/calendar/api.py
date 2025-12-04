from rest_framework import viewsets
from rest_framework.exceptions import NotFound
from rest_framework.renderers import BrowsableAPIRenderer

from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.models import BaseTagObject
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus_event.calendar.permissions import CalendarPublicEventPermissions
from cosinnus_event.calendar.serializers import (
    CalendarPublicEventListQueryParameterSerializer,
    CalendarPublicEventListSerializer,
    CalendarPublicEventSerializer,
)
from cosinnus_event.models import Event


class CalendarPublicEventViewSet(viewsets.ModelViewSet):
    """
    Viewset for public events for the v3 calendar app.
    """

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    serializer_class = CalendarPublicEventSerializer
    serializer_class_query = CalendarPublicEventListQueryParameterSerializer
    permission_classes = (CalendarPublicEventPermissions,)
    pagination_class = None

    group = None
    query_params = None

    def get_serializer_class(self):
        if self.action == 'list':
            # use a different serializer for the list view, containing a subset of fields
            return CalendarPublicEventListSerializer
        return self.serializer_class

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['group'] = self.group
        return context

    def initial(self, request, *args, **kwargs):
        # get group from slug
        group_id = kwargs.get('group_id')
        self.group = get_cosinnus_group_model().objects.filter(is_active=True, pk=group_id).first()
        if not self.group:
            raise NotFound()
        return super().initial(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        # validate and set query parameters
        query_params_serializer = CalendarPublicEventListQueryParameterSerializer(data=request.query_params)
        if query_params_serializer.is_valid(raise_exception=True):
            self.query_params = query_params_serializer.validated_data
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Event.objects.all()
        queryset = queryset.prefetch_related('media_tag')
        queryset = queryset.filter(media_tag__visibility=BaseTagObject.VISIBILITY_ALL)
        queryset = queryset.filter(group=self.group)
        if self.action == 'list':
            # apply query parameters
            queryset = queryset.filter(
                from_date__date__gte=self.query_params['from_date'], to_date__date__lte=self.query_params['to_date']
            )
        return queryset
