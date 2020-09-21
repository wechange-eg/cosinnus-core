from rest_framework import viewsets, pagination

from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus_conference.api.serializers import ConferenceSerializer, ConferenceEventSerializer
from cosinnus_event.models import ConferenceEvent


# FIXME: Make this pagination class default in REST_FRAMEWORK setting
class DefaultPageNumberPagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 1000


class RequireGroupReadMixin(object):

    def get_queryset(self):
        user_group_ids = get_cosinnus_group_model().objects.get_for_user_pks(self.request.user)
        return self.queryset.filter(id__in=user_group_ids)


class RequireEventReadMixin(object):

    def get_queryset(self):
        user_group_ids = get_cosinnus_group_model().objects.get_for_user_pks(self.request.user)
        return self.queryset.filter(room__group__id__in=user_group_ids)


class ConferenceViewSet(RequireGroupReadMixin,
                        viewsets.ReadOnlyModelViewSet):
    queryset = get_cosinnus_group_model().objects.filter(is_conference=True, is_active=True)
    serializer_class = ConferenceSerializer


class ConferenceEventViewSet(RequireEventReadMixin,
                             viewsets.ReadOnlyModelViewSet):
    queryset = ConferenceEvent.objects.filter(room__group__is_conference=True, room__group__is_active=True)
    serializer_class = ConferenceEventSerializer
    pagination_class = DefaultPageNumberPagination

    def get_queryset(self):
        queryset = super().get_queryset().conference_upcoming()

        # Filter by room or conference
        room_id = self.request.GET.get('room_id')
        conference_id = self.request.GET.get('conference_id')
        if room_id:
            queryset = queryset.filter(room=room_id)
        elif conference_id:
            queryset = queryset.filter(room__group=conference_id).exclude(type__in=ConferenceEvent.TIMELESS_TYPES)
        else:
            queryset = queryset.none()

        return queryset

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