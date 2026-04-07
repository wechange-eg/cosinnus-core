from rest_framework import viewsets
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
from cosinnus.conf import settings
from cosinnus.models import BaseTagObject
from cosinnus.utils.group import get_cosinnus_group_model
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
)
from cosinnus_event.models import Event


class CosinnusCalendarViewSet(viewsets.ModelViewSet):
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
    reflections_enabled = 'cosinnus_event.event' in settings.COSINNUS_REFLECTABLE_OBJECTS

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

    def list(self, request, *args, **kwargs):
        # validate and set query parameters
        query_params_serializer = CosinnusCalendarListQueryParameterSerializer(data=request.query_params)
        query_params_serializer.is_valid(raise_exception=True)
        self.query_params = query_params_serializer.validated_data
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Event.objects.all()
        queryset = queryset.filter(group=self.group)
        if self.reflections_enabled:
            queryset = MixReflectedObjectsMixin().mix_queryset(queryset, Event, self.group)
        queryset = queryset.prefetch_related('media_tag', 'attendances')
        queryset = queryset.filter(media_tag__visibility=BaseTagObject.VISIBILITY_ALL)
        queryset = queryset.filter(state=Event.STATE_SCHEDULED)
        if self.action == 'list':
            # apply query parameters
            queryset = queryset.filter(
                from_date__date__gte=self.query_params['from_date'], to_date__date__lte=self.query_params['to_date']
            )
        return queryset

    @action(
        detail=True,
        methods=['get', 'post'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[CosinnusCalendarPermissions],
    )
    def attendance(self, request, group_id, pk=None):
        """
        Set event attendance for request user.
        Serializer is set in get_serializer_class.
        Note: Implemented as extra action and not a field in the event serializer, because of different permissions.
              Users with only read permissions to the event should be able to set it.
        """
        instance = self.get_object()
        if request.method == 'GET':
            serializer = self.get_serializer(instance)
        else:
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['post'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[CosinnusCalendarPermissions],
        parser_classes=[MultiPartParser],
    )
    def attach_file(self, request, group_id, pk=None):
        """
        Action to upload an attachment for an event.
        Serializer is set in get_serializer_class.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response()

    @action(
        detail=True,
        methods=['post'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[CosinnusCalendarPermissions],
    )
    def delete_attached_file(self, request, group_id, pk=None):
        """
        Action to delete an attachment.
        Serializer is set in get_serializer_class.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response()

    @action(
        detail=True,
        methods=['get', 'patch', 'post'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[CosinnusCalendarPermissions],
    )
    def bbb_room(self, request, group_id, pk=None):
        """
        BBB Room and conference settings API.
        Serializer is set in get_serializer_class.
        """
        instance = self.get_object()
        if request.method == 'GET':
            serializer = self.get_serializer(instance)
        else:
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['get'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[CosinnusCalendarPermissions],
    )
    def bbb_room_urls(self, request, group_id, pk=None):
        """
        API for BBB room Urls, used for periodic pull during BBB room creation.
        Serializer is set in get_serializer_class.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['get', 'post'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[CosinnusCalendarPermissions],
    )
    def bookmark(self, request, group_id, pk=None):
        """
        API to bookmark the event.
        Serializer is set in get_serializer_class.
        """
        instance = self.get_object()
        if request.method == 'GET':
            serializer = self.get_serializer(instance)
        else:
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
        return Response(serializer.data)

    @action(
        detail=True,
        methods=['get', 'patch', 'post'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[CosinnusCalendarPermissions],
    )
    def reflections(self, request, group_id, pk=None):
        """
        API to handle event reflection in user groups.
        Serializer is set in get_serializer_class.
        """
        data = {}
        if self.reflections_enabled:
            instance = self.get_object()
            # TODO: make action code more DRY.
            if request.method == 'GET':
                serializer = self.get_serializer(instance)
            else:
                serializer = self.get_serializer(instance, data=request.data)
                serializer.is_valid(raise_exception=True)
                serializer.save()
            data = serializer.data
        return Response(data)
