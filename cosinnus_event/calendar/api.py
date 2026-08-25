import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.parsers import MultiPartParser
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from cosinnus import VERSION as COSINNUS_VERSION
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
from cosinnus_cloud.hooks import get_nc_user_id
from cosinnus_cloud.utils import nextcloud
from cosinnus_cloud.utils.cosinnus import is_calendar_enabled_for_group
from cosinnus_event.calendar.nextcloud_caldav import NextcloudCaldavConnection
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

logger = logging.getLogger('cosinnus')


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


class CalendarRepairMembershipView(APIView):
    """
    Attempts to repair a missing or faulty user group membership in the nextcloud group for the given CosinnusGroup.
    Also re-shares the nextcloud calendar for the group.
    """

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (IsCosinnusGroupUser,)

    group = None

    def initial(self, request, *args, **kwargs):
        # get group
        group_id = kwargs.get('group_id')
        self.group = get_cosinnus_group_model().objects.filter(is_active=True, pk=group_id).first()
        if not self.group:
            raise NotFound()
        return super().initial(request, *args, **kwargs)

    @swagger_auto_schema(
        responses={
            200: openapi.Response(
                description='Success.',
                examples={
                    'application/json': {
                        'data': {'status': 'ok'},
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            ),
            403: openapi.Response(
                description='Bad Request',
                examples={
                    'application/json': {
                        'data': {'detail': 'Rate-limited.'},
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            ),
            503: openapi.Response(
                description='Internal cloud error',
                examples={
                    'application/json': {
                        'data': {'error': 'Internal cloud error', 'message': '(passed through message)'},
                        'version': COSINNUS_VERSION,
                        'timestamp': 1658414865.057476,
                    }
                },
            ),
        }
    )
    def post(self, request, group_id):
        if not is_calendar_enabled_for_group(self.group):
            return Response(status=status.HTTP_403_FORBIDDEN, data={'detail': 'Calendar not enabled for group.'})
        if not self.group.is_active or 'cosinnus_event' in self.group.get_deactivated_apps():
            return Response(
                status=status.HTTP_403_FORBIDDEN, data={'detail': 'Group or group event app is not active.'}
            )
        if not self.group.nextcloud_group_id or not self.group.nextcloud_calendar_url:
            return Response(status=status.HTTP_403_FORBIDDEN, data={'detail': 'Calendar not initialized for group.'})

        # log this so we can track the number of repairs happening
        logger.warning(
            'Info: CalendarRepairMembershipView has been called to repair a group membership',
            extra={
                'user_id': request.user.id,
                'group_id': group_id,
            },
        )

        is_rate_limited = False
        if is_rate_limited:
            return Response(status=status.HTTP_403_FORBIDDEN, data={'error': 'Rate-limited.'})

        nc_uid = get_nc_user_id(request.user)
        nc_group_id = self.group.nextcloud_group_id

        try:
            # add user to NC group. group member checks have been done by permission_classes `IsCosinnusGroupUser`.
            nextcloud.add_user_to_group(nc_uid, nc_group_id)

            # re-do calendar share for the group. will have no effect if the calendar is properly shared already
            calendar = NextcloudCaldavConnection()
            calendar.group_calendar_share(self.group)
        except Exception as e:
            return Response(
                status=status.HTTP_503_SERVICE_UNAVAILABLE, data={'error': 'Internal cloud error', 'message': str(e)}
            )

        return Response(data={'status': 'ok'})
