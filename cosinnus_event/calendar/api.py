from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.parsers import MultiPartParser
from rest_framework.renderers import BrowsableAPIRenderer
from rest_framework.response import Response

from cosinnus.api_frontend.handlers.renderers import CosinnusAPIFrontendJSONResponseRenderer
from cosinnus.api_frontend.serializers.attached_objects import AttachFileSerializer, DeleteAttachedFileSerializer
from cosinnus.api_frontend.views.user import CsrfExemptSessionAuthentication
from cosinnus.models import BaseTagObject
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus_event.calendar.permissions import CalendarPublicEventPermissions
from cosinnus_event.calendar.serializers import (
    CalendarPublicEventAttendanceActionSerializer,
    CalendarPublicEventBBBRoomActionSerializer,
    CalendarPublicEventBBBRoomUrlsActionSerializer,
    CalendarPublicEventListQueryParameterSerializer,
    CalendarPublicEventListSerializer,
    CalendarPublicEventSerializer,
)
from cosinnus_event.models import Event, EventAttendance


class CalendarPublicEventViewSet(viewsets.ModelViewSet):
    """
    Viewset for public events for the v3 calendar app.
    """

    renderer_classes = (
        CosinnusAPIFrontendJSONResponseRenderer,
        BrowsableAPIRenderer,
    )
    serializer_class = CalendarPublicEventSerializer
    authentication_classes = (CsrfExemptSessionAuthentication,)
    permission_classes = (CalendarPublicEventPermissions,)
    pagination_class = None

    group = None
    query_params = None

    def get_serializer_class(self):
        if self.action == 'list':
            # use a different serializer for the list view, containing a subset of fields
            return CalendarPublicEventListSerializer
        elif self.action == 'attendance':
            return CalendarPublicEventAttendanceActionSerializer
        elif self.action == 'attach_file':
            return AttachFileSerializer
        elif self.action == 'delete_attached_file':
            return DeleteAttachedFileSerializer
        elif self.action == 'bbb_room':
            return CalendarPublicEventBBBRoomActionSerializer
        elif self.action == 'bbb_room_urls':
            return CalendarPublicEventBBBRoomUrlsActionSerializer
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
        query_params_serializer.is_valid(raise_exception=True)
        self.query_params = query_params_serializer.validated_data
        return super().list(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Event.objects.all()
        queryset = queryset.prefetch_related('media_tag', 'attendances')
        queryset = queryset.filter(media_tag__visibility=BaseTagObject.VISIBILITY_ALL)
        queryset = queryset.filter(group=self.group)
        queryset = queryset.filter(state=Event.STATE_SCHEDULED)
        if self.action == 'list':
            # apply query parameters
            queryset = queryset.filter(
                from_date__date__gte=self.query_params['from_date'], to_date__date__lte=self.query_params['to_date']
            )
        return queryset

    @action(
        detail=True,
        methods=['post'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[CalendarPublicEventPermissions],
    )
    def attendance(self, request, group_id, pk=None):
        """
        Set event attendance for request user.
        Serializer is set in get_serializer_class.
        Note: Implemented as extra action and not a field in the event serializer, because of different permissions.
              Users with only read permissions to the event should be able to set it.
        """
        instance = self.get_object()
        user = request.user
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attending = serializer.validated_data['attending']
        user_attendance = instance.attendances.filter(user=user).first()
        if attending:
            # user is attending
            if user_attendance:
                if user_attendance.state != EventAttendance.ATTENDANCE_GOING:
                    # set state to "going" of existing event attendance
                    user_attendance.state = EventAttendance.ATTENDANCE_GOING
                    user_attendance.save()
            else:
                # no event attendance exists, create a new one
                instance.attendances.create(user=user, state=EventAttendance.ATTENDANCE_GOING)
        elif user_attendance and user_attendance.state != EventAttendance.ATTENDANCE_NOT_GOING:
            # user not attending, but event attendance exists, set state to "not going"
            user_attendance.state = EventAttendance.ATTENDANCE_NOT_GOING
            user_attendance.save()
        return Response()

    @action(
        detail=True,
        methods=['post'],
        authentication_classes=[CsrfExemptSessionAuthentication],
        permission_classes=[CalendarPublicEventPermissions],
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
        permission_classes=[CalendarPublicEventPermissions],
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
        permission_classes=[CalendarPublicEventPermissions],
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
        permission_classes=[CalendarPublicEventPermissions],
    )
    def bbb_room_urls(self, request, group_id, pk=None):
        """
        API for BBB room Urls, used for periodic pull during BBB room creation.
        Serializer is set in get_serializer_class.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
