from django.contrib.auth import get_user_model
from rest_framework import viewsets, pagination

from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus_conference.api.serializers import ConferenceSerializer, ConferenceEventSerializer, \
    ConferenceParticipantSerializer, ConferenceEventParticipantsSerializer
from cosinnus_event.models import ConferenceEvent


# FIXME: Make this pagination class default in REST_FRAMEWORK setting
from rest_framework.decorators import action
from cosinnus.utils.permissions import check_user_superuser
from cosinnus.models.group_extra import CosinnusConference


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


class ConferenceViewSet(RequireGroupReadMixin,
                        viewsets.ReadOnlyModelViewSet):
    queryset = CosinnusConference.objects.filter(is_active=True)
    serializer_class = ConferenceSerializer
    pagination_class = DefaultPageNumberPagination

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
    def organisations(self, request, pk=None):
        return Response([
            {
                "id": 1,
                "name": "Organisation 1",
                "description": "Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet.",
                "topics": ["One", "Two", "Three"],
                "location": "Location",
                "image_url": "/path/to/image.png",
            },
            {
                "id": 2,
                "name": "Organisation 2",
                "description": "Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet.",
                "topics": ["One", "Two", "Three"],
                "location": "Location",
                "image_url": "/path/to/image.png",
            },
            {
                "id": 3,
                "name": "Organisation 3",
                "description": "Lorem ipsum dolor sit amet, consetetur sadipscing elitr, sed diam nonumy eirmod tempor invidunt ut labore et dolore magna aliquyam erat, sed diam voluptua. At vero eos et accusam et justo duo dolores et ea rebum. Stet clita kasd gubergren, no sea takimata sanctus est Lorem ipsum dolor sit amet.",
                "topics": ["One", "Two", "Three"],
                "location": "Location",
                "image_url": "/path/to/image.png",
            },
        ])
"""
