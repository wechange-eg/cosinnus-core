from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.parsers import MultiPartParser
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response

from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.api_frontend.serializers.attached_objects import (
    CosinnusAttachFileSerializer,
    CosinnusDeleteAttachedFileSerializer,
)
from cosinnus.api_frontend.serializers.tagged import CosinnusTagObjectBookmarkSerializer
from cosinnus.api_frontend.views.user import CsrfExemptSessionAuthentication
from cosinnus.models import BaseTagObject
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.permissions import IsCosinnusGroupUser
from cosinnus.views.mixins.reflected_objects import MixReflectedObjectsMixin
from cosinnus_event.calendar.permissions import CosinnusCalendarPermissions
from cosinnus_event.calendar.serializers import (
    CosinnusCalendarBBBRoomUrlsSerializer,
    CosinnusCalendarEventAttendanceSerializer,
    CosinnusCalendarEventBBBRoomSerializer,
    CosinnusCalendarEventReflectSerializer,
    CosinnusCalendarEventSerializer,
    CosinnusCalendarListQueryParameterSerializer,
    CosinnusCalendarListSerializer,
    CosinnusCalendarSyncedEventListSerializer,
    CosinnusCalendarSyncedEventSerializer,
    CosinnusCalendarSynceRequiredSerializer,
)
from cosinnus_event.models import Event


class ViewSetActionMixin:
    """Viewset mixin for generic serializer based action processing."""

    def process_action(self, request, partial=False):
        """
        Generic helper to handle viewset actions using the serializer set in get_serializer_class.
        @return: serialized data
        """
        instance = self.get_object()
        if request.method == 'GET':
            serializer = self.get_serializer(instance)
        else:
            serializer = self.get_serializer(instance, data=request.data, partial=partial)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return serializer.data


class ListQueryParamsMixin:
    """Filters the list view queryset by "from_date" and "to_date" query parameters."""

    query_params = None

    def list(self, request, *args, **kwargs):
        # validate and set query parameters
        query_params_serializer = CosinnusCalendarListQueryParameterSerializer(data=request.query_params)
        query_params_serializer.is_valid(raise_exception=True)
        self.query_params = query_params_serializer.validated_data
        return super().list(request, *args, **kwargs)

    def filter_by_query_params(self, queryset):
        # apply query parameter to queryset
        return queryset.filter(
            from_date__date__gte=self.query_params['from_date'], to_date__date__lte=self.query_params['to_date']
        )


class CosinnusCalendarViewSet(ViewSetActionMixin, ListQueryParamsMixin, viewsets.ModelViewSet):
    """
    Viewset for public events for the v3 calendar app.
    """

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    serializer_class = CosinnusCalendarEventSerializer
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (CosinnusCalendarPermissions,)
    pagination_class = None

    group = None
    query_params = None

    def get_serializer_class(self):
        """Get serializer based on viewset action."""
        action_serializers = {
            'list': CosinnusCalendarListSerializer,
            'attendance': CosinnusCalendarEventAttendanceSerializer,
            'attach_file': CosinnusAttachFileSerializer,
            'delete_attached_file': CosinnusDeleteAttachedFileSerializer,
            'bbb_room': CosinnusCalendarEventBBBRoomSerializer,
            'bbb_room_urls': CosinnusCalendarBBBRoomUrlsSerializer,
            'bookmark': CosinnusTagObjectBookmarkSerializer,
            'reflections': CosinnusCalendarEventReflectSerializer,
        }
        if self.action in action_serializers:
            return action_serializers[self.action]
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

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            # queryset just for schema generation metadata
            return Event.objects.none()
        queryset = Event.objects.filter(group=self.group)
        queryset = MixReflectedObjectsMixin().mix_queryset(queryset, Event, self.group)
        queryset = queryset.prefetch_related('media_tag', 'attendances')
        queryset = queryset.filter(
            media_tag__visibility=BaseTagObject.VISIBILITY_ALL, state=Event.STATE_SCHEDULED, is_hidden_group_proxy=False
        )
        if self.action == 'list':
            # apply query parameters
            queryset = self.filter_by_query_params(queryset)
        return queryset

    def get_object(self):
        event = super().get_object()
        # check that the event belongs to the group referenced in the url
        if event.group_id != self.group.id:
            raise NotFound()
        return event

    @action(
        detail=True,
        methods=['get', 'post'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[CosinnusCalendarPermissions],
    )
    def attendance(self, request, group_id, pk=None):
        """
        Set event attendance for request user.
        Note: Implemented as extra action and not a field in the event serializer, because of different permissions.
              Users with only read permissions to the event should be able to set it.
        """
        data = self.process_action(request)
        return Response(data)

    @action(
        detail=True,
        methods=['post'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[CosinnusCalendarPermissions],
        parser_classes=[MultiPartParser],
    )
    def attach_file(self, request, group_id, pk=None):
        """Action to upload an attachment for an event."""
        data = self.process_action(request)
        return Response(data)

    @action(
        detail=True,
        methods=['post'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[CosinnusCalendarPermissions],
    )
    def delete_attached_file(self, request, group_id, pk=None):
        """Action to delete an attachment."""
        data = self.process_action(request)
        return Response(data)

    @action(
        detail=True,
        methods=['get', 'patch', 'post'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[CosinnusCalendarPermissions],
    )
    def bbb_room(self, request, group_id, pk=None):
        """BBB Room and conference settings API."""
        data = self.process_action(request, partial=True)
        return Response(data)

    @action(
        detail=True,
        methods=['get'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[CosinnusCalendarPermissions],
    )
    def bbb_room_urls(self, request, group_id, pk=None):
        """API for BBB room Urls, used for periodic pull during BBB room creation"""
        data = self.process_action(request)
        return Response(data)

    @action(
        detail=True,
        methods=['get', 'post'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[CosinnusCalendarPermissions],
    )
    def bookmark(self, request, group_id, pk=None):
        """API to bookmark the event."""
        data = self.process_action(request)
        return Response(data)

    @action(
        detail=True,
        methods=['get', 'patch', 'post'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[CosinnusCalendarPermissions],
    )
    def reflections(self, request, group_id, pk=None):
        """API to handle event reflection in user groups"""
        data = self.process_action(request)
        return Response(data)


class CosinnusCalendarSyncedEventsViewSet(
    ViewSetActionMixin,
    ListQueryParamsMixin,
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """
    Viewset for synced private events for the v3 calendar app.
    """

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    lookup_field = 'nextcloud_calendar_uid'
    serializer_class = CosinnusCalendarSyncedEventSerializer
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsCosinnusGroupUser,)
    pagination_class = None

    group = None

    def get_serializer_class(self):
        """Get serializer based on viewset action."""
        action_serializers = {
            'list': CosinnusCalendarSyncedEventListSerializer,
            'attendance': CosinnusCalendarEventAttendanceSerializer,
            'bbb_room': CosinnusCalendarEventBBBRoomSerializer,
            'bbb_room_urls': CosinnusCalendarBBBRoomUrlsSerializer,
            'sync_required': CosinnusCalendarSynceRequiredSerializer,
        }
        if self.action in action_serializers:
            return action_serializers[self.action]
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

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            # queryset just for schema generation metadata
            return Event.objects.none()
        queryset = Event.objects.filter(group=self.group)
        queryset = queryset.prefetch_related('media_tag', 'attendances')
        queryset = queryset.filter(
            media_tag__visibility=BaseTagObject.VISIBILITY_GROUP,
            state=Event.STATE_SYNCHRONIZED_EVENT,
            is_hidden_group_proxy=False,
        ).exclude(
            nextcloud_calendar_uid=None,
        )
        if self.action == 'list':
            # apply query parameters
            queryset = self.filter_by_query_params(queryset)
        return queryset

    def get_object(self):
        event = super().get_object()
        # check that the event belongs to the group referenced in the url
        if event.group_id != self.group.id:
            raise NotFound()
        return event

    @action(
        detail=True,
        methods=['get', 'post'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[IsCosinnusGroupUser],
    )
    def attendance(self, request, group_id, nextcloud_calendar_uid):
        """
        Set event attendance for request user.
        Note: Implemented as extra action and not a field in the event serializer, because of different permissions.
              Users with only read permissions to the event should be able to set it.
        """
        data = self.process_action(request)
        return Response(data)

    @action(
        detail=True,
        methods=['get', 'patch', 'post'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[IsCosinnusGroupUser],
    )
    def bbb_room(self, request, group_id, nextcloud_calendar_uid):
        """BBB Room and conference settings API."""
        data = self.process_action(request, partial=True)
        return Response(data)

    @action(
        detail=True,
        methods=['get'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[IsCosinnusGroupUser],
    )
    def bbb_room_urls(self, request, group_id, nextcloud_calendar_uid):
        """API for BBB room Urls, used for periodic pull during BBB room creation"""
        data = self.process_action(request)
        return Response(data)

    @action(
        detail=False,
        methods=['post', 'put'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[IsCosinnusGroupUser],
    )
    def sync_required(self, request, group_id):
        """API to inform the Backend that a Caldav sync is required due to changes to internal events."""
        # TODO: remove unused feature, if ctag sync works
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
