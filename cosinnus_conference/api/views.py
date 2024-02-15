from django.contrib.auth import get_user_model
from rest_framework import viewsets, pagination
from rest_framework.response import Response

from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus_conference.api.serializers import ConferenceSerializer, ConferenceEventSerializer, \
    ConferenceParticipantSerializer, ConferenceEventParticipantsSerializer
from cosinnus_event.models import ConferenceEvent, ConferenceEventAttendanceTracking, Event


# FIXME: Make this pagination class default in REST_FRAMEWORK setting
from rest_framework.decorators import action
from cosinnus.utils.permissions import check_user_superuser, check_object_write_access, check_object_read_access
from cosinnus.models.group_extra import CosinnusConference, CosinnusGroup
from cosinnus.api.views.mixins import CosinnusFilterQuerySetMixin,\
    PublicCosinnusGroupFilterMixin, CosinnusPaginateMixin
from copy import copy
from django.utils.timezone import now
from django.db.models import Q


class DefaultPageNumberPagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 1000


class RequireGroupReadMixin(object):

    def get_queryset(self):
        queryset = self.queryset
        if not check_user_superuser(self.request.user):
            user_group_ids = get_cosinnus_group_model().objects.get_for_user_pks(self.request.user)
            queryset = queryset.filter(id__in=user_group_ids)
        return queryset


class RequireEventReadMixin(object):

    def get_queryset(self):
        queryset = self.queryset
        if not check_user_superuser(self.request.user):
            user_group_ids = get_cosinnus_group_model().objects.get_for_user_pks(self.request.user)
            queryset = queryset.filter(room__group__id__in=user_group_ids, room__is_visible=True)
        return queryset


class BaseConferenceViewSet(CosinnusFilterQuerySetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = CosinnusConference.objects.filter(is_active=True)
    serializer_class = ConferenceSerializer
    
    FILTER_CONDITION_MAP = copy(CosinnusFilterQuerySetMixin.FILTER_CONDITION_MAP)
    FILTER_CONDITION_MAP.update({
        'upcoming': {
            'true': [Q(to_date__gte=now())]
        }
    })
    FILTER_DEFAULT_ORDER = ['from_date', ]
    

class PublicConferenceViewSet(CosinnusPaginateMixin, PublicCosinnusGroupFilterMixin,
                             BaseConferenceViewSet):
    
    pass
        

class ConferenceViewSet(RequireGroupReadMixin, BaseConferenceViewSet):

    @action(detail=True, methods=['get'])
    def events(self, request, pk=None):
        queryset = ConferenceEvent.objects
        room_id = self.request.GET.get('room_id')
        if room_id:
            queryset = queryset.filter(room=room_id)
        else:
            queryset = queryset.filter(room__group=pk)\
                .exclude(type__in=ConferenceEvent.TIMELESS_TYPES)\
                .filter(room__is_visible=True)
        queryset = queryset.order_by('from_date', 'title')
        page = self.paginate_queryset(queryset)
        serializer = ConferenceEventSerializer(page, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['get'])
    def participants(self, request, pk=None):
        queryset = self.get_object().actual_members.order_by('first_name', 'last_name')
        page = self.paginate_queryset(queryset)
        serializer = ConferenceParticipantSerializer(page, many=True, context={"request": request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=['get'])
    def event_participants(self, request, pk=None):
        queryset = ConferenceEvent.objects
        room_id = self.request.GET.get('room_id')
        if room_id:
            queryset = queryset.filter(room=room_id)
        else:
            queryset = queryset.filter(room__group=pk).exclude(type__in=ConferenceEvent.TIMELESS_TYPES)
        queryset = queryset.order_by('from_date')
        page = self.paginate_queryset(queryset)
        serializer = ConferenceEventParticipantsSerializer(page, many=True, context={"request": request})
        return self.get_paginated_response({p['id']: p['participants_count'] for p in serializer.data})

    @action(detail=False, methods=['get'])
    def invitation(self, request):
        """
        Returns conference invitation text and alert text.
        Uses the "object_type" and "object_id" parameters to get the object containing the BBB room. If the "guest"
        parameter is "true" returns the invitation text with the BBB guest join URL, otherwise the URL of the
        object is used.
        """
        response = {
            'alert_text': None,
            'invitation': None,
        }

        # Get the object containing the BBB room.
        object_type = self.request.GET.get('object_type')
        object_id = self.request.GET.get('object_id')
        guest_invitation = self.request.GET.get('guest') == 'true'
        object_class = None
        obj = None
        if object_type == 'group':
            object_class = CosinnusGroup
        elif object_type == 'event':
            object_class = Event
        elif object_type == 'conference_event':
            object_class = ConferenceEvent

        if object_class and object_id:
            obj = object_class.objects.filter(id=object_id).first()
        if not obj:
            return Response(status=404)

        # Check access permissions
        if not check_object_read_access(obj, request.user):
            return Response(status=403)

        bbb_room = getattr(obj.media_tag, 'bbb_room', None)
        if bbb_room:
            # Get invitation text.
            if guest_invitation and check_object_write_access(obj, request.user):
                # Use guest invitation text.
                invitation = bbb_room.get_invitation_text()
            else:
                # Use platform-user invitation text.
                invitation = bbb_room.get_invitation_text(obj.get_absolute_url())
            response['invitation'] = invitation

            # Get the alert message.
            response['alert_text'] = bbb_room.get_invitation_alert_text()

        return Response(response)

    @action(detail=True, methods=['get'])
    def attend_event(self, request, pk=None):
        """ Track user attendance via ConferenceEventAttendanceTracking. """
        event_id = self.request.GET.get('event_id')
        event = ConferenceEvent.objects.get(id=event_id)
        if not event:
            return Response(status=404)
        ConferenceEventAttendanceTracking.track_attendance(request.user, event)
        return Response(status=200)

"""
    @action(detail=True, methods=['get'])
    def networking(self, request, pk=None):
        return Response([
            {
                "id": 1,
                "name": "Completely random",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
            },
            {
                "id": 2,
                "name": "Someone who you are not connected with",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
            },
            {
                "id": 3,
                "name": "Someone who is based in another country than you",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
            },
            {
                "id": 4,
                "name": "Someone who is working on the same topic(s)",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
            },
            {
                "id": 5,
                "name": "Someone who is a cat person",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
            },
            {
                "id":6,
                "name": "Someone who is a dog person",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
            },
        ])

    @action(detail=True, methods=['get'])
    def organizations(self, request, pk=None):
        return Response([
            {
                "id": 1,
                "name": "Organization 1",
                "description": "Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet.",
                "topics": ["One", "Two", "Three"],
                "location": "Location",
                "image_url": "/path/to/image.png",
            },
            {
                "id": 2,
                "name": "Organization 2",
                "description": "Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet.",
                "topics": ["One", "Two", "Three"],
                "location": "Location",
                "image_url": "/path/to/image.png",
            },
            {
                "id": 3,
                "name": "Organization 3",
                "description": "Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet.",
                "topics": ["One", "Two", "Three"],
                "location": "Location",
                "image_url": "/path/to/image.png",
            },
        ])
"""
