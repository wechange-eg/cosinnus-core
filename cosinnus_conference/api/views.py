from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from cosinnus_conference.api.serializers import ConferenceSerializer
from cosinnus.api.views import CosinnusFilterQuerySetMixin, PublicCosinnusGroupFilterMixin
from cosinnus.models.group_extra import CosinnusGroup


class ConferenceViewSet(CosinnusFilterQuerySetMixin,
                        PublicCosinnusGroupFilterMixin,
                        viewsets.ReadOnlyModelViewSet):
    # FIXME: Return only Groups that are conferences
    queryset = CosinnusGroup.objects.all()
    serializer_class = ConferenceSerializer

    @action(detail=True, methods=['get'])
    def lobby(self, request, pk=None):
        return Response([
            {
                "id": 1,
                "name": "Check In",
                "description": "Try the public Chat LOBBY or ask for help: TEAM SUPPORT",
                "from_time": "2020-09-14 08:30:00 UTC",
                "to_time": "2020-09-14 09:15:00 UTC",
                "room_name": "Chat LOBBY",
                "room_slug": "lobby",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
            },
            {
                "id": 2,
                "name": "Offline Eco-Communities 1",
                "description": "Ilona Gebauer, Thomas Krüger",
                "from_time": "2020-09-14 09:15:00 UTC",
                "to_time": "2020-09-14 10:30:00 UTC",
                "room_name": "Open discussions 1",
                "room_slug": "discussions-1",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
            },
            {
                "id": 3,
                "name": "Offline Eco-Communities 2",
                "description": "Ilona Gebauer, Thomas Krüger",
                "from_time": "2020-09-14 09:15:00 UTC",
                "to_time": "2020-09-14 10:30:00 UTC",
                "room_name": "Open discussions 2",
                "room_slug": "discussions-2",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
            },
            {
                "name": "Pause",
                "from_time": "2020-09-14 10:30:00 UTC",
                "to_time": "2020-09-14 11:00:00 UTC"
            },
            {
                "id": 4,
                "name": "Offline Eco-Communities 3",
                "description": "Ilona Gebauer, Thomas Krüger",
                "from_time": "2020-09-14 11:000:00 UTC",
                "to_time": "2020-09-14 11:30:00 UTC",
                "room_name": "Open discussions 3",
                "room_slug": "discussions-3",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
            },
            {
                "id": 5,
                "name": "Offline Eco-Communities 4",
                "description": "Ilona Gebauer, Thomas Krüger",
                "from_time": "2020-09-14 11:000:00 UTC",
                "to_time": "2020-09-14 11:30:00 UTC",
                "room_name": "Open discussions 4",
                "room_slug": "discussions-4",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
            },
        ])

    @action(detail=True, methods=['get'])
    def stage(self, request, pk=None):
        return Response([
            {
                "id": 2,
                "name": "Offline Eco-Communities 1",
                "description": "Ilona Gebauer, Thomas Krüger",
                "from_time": "2020-09-14 09:15:00 UTC",
                "to_time": "2020-09-14 10:30:00 UTC",
                "room_name": "Stage",
                "room_slug": "stage-1",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
            },
        ])

    @action(detail=True, methods=['get'])
    def discussions(self, request, pk=None):
        return Response([
            {
                "id": 2,
                "name": "Offline Eco-Communities 1",
                "description": "Ilona Gebauer, Thomas Krüger",
                "from_time": "2020-09-14 09:15:00 UTC",
                "to_time": "2020-09-14 10:30:00 UTC",
                "room_name": "Open discussions 1",
                "room_slug": "discussions-1",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
            },
            {
                "id": 3,
                "name": "Offline Eco-Communities 2",
                "description": "Ilona Gebauer, Thomas Krüger",
                "from_time": "2020-09-14 09:15:00 UTC",
                "to_time": "2020-09-14 10:30:00 UTC",
                "room_name": "Open discussions 2",
                "room_slug": "discussions-2",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
            },
            {
                "id": 4,
                "name": "Offline Eco-Communities 3",
                "description": "Ilona Gebauer, Thomas Krüger",
                "from_time": "2020-09-14 11:000:00 UTC",
                "to_time": "2020-09-14 11:30:00 UTC",
                "room_name": "Open discussions 3",
                "room_slug": "discussions-3",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
            },
            {
                "id": 5,
                "name": "Offline Eco-Communities 4",
                "description": "Ilona Gebauer, Thomas Krüger",
                "from_time": "2020-09-14 11:000:00 UTC",
                "to_time": "2020-09-14 11:30:00 UTC",
                "room_name": "Open discussions 4",
                "room_slug": "discussions-4",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
            },
        ])

    @action(detail=True, methods=['get'])
    def workshops(self, request, pk=None):
        return Response([
            {
                "id": 1,
                "name": "Workshop 1",
                "description": "Ilona Gebauer, Thomas Krüger",
                "from_time": "2020-09-14 09:15:00 UTC",
                "to_time": "2020-09-14 10:30:00 UTC",
                "room_name": "Workshop 1",
                "room_slug": "workshops-1",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
                "participants_count": 34
            },
            {
                "id": 2,
                "name": "Workshop 2",
                "description": "Ilona Gebauer, Thomas Krüger",
                "from_time": "2020-09-14 09:15:00 UTC",
                "to_time": "2020-09-14 10:30:00 UTC",
                "room_name": "Workshop 2",
                "room_slug": "workshops-2",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
                "participants_count": 34
            },
            {
                "id": 3,
                "name": "Workshop 3",
                "description": "Ilona Gebauer, Thomas Krüger",
                "from_time": "2020-09-14 11:000:00 UTC",
                "to_time": "2020-09-14 11:30:00 UTC",
                "room_name": "Workshop 3",
                "room_slug": "workshops-3",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
                "participants_count": 34
            },
            {
                "id": 4,
                "name": "Workshop 4",
                "description": "Ilona Gebauer, Thomas Krüger",
                "from_time": "2020-09-14 11:000:00 UTC",
                "to_time": "2020-09-14 11:30:00 UTC",
                "room_name": "Workshop 4",
                "room_slug": "workshops-4",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
                "participants_count": 34
            },
        ])

    @action(detail=True, methods=['get'], url_path="coffee-tables")
    def coffee_tables(self, request, pk=None):
        return Response([
            {
                "id": 1,
                "name": "Topic of the coffee table",
                "image_url": "/path/to/image.png",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
                "participants": [
                    {
                        "id": 1,
                        "first_name": "Vorname",
                        "last_name": "Nachname",
                        "organisation": "Organisation",
                        "location": "Location",
                    },
                    {
                        "id": 2,
                        "first_name": "Vorname",
                        "last_name": "Nachname",
                        "organisation": "Organisation",
                        "location": "Location",
                    },
                    {
                        "id": 3,
                        "first_name": "Vorname",
                        "last_name": "Nachname",
                        "organisation": "Organisation",
                        "location": "Location",
                    },
                ]
            },
            {
                "id": 2,
                "name": "Topic of the coffee table",
                "image_url": "/path/to/image.png",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
                "participants": [
                    {
                        "id": 1,
                        "first_name": "Vorname",
                        "last_name": "Nachname",
                        "organisation": "Organisation",
                        "location": "Location",
                    },
                    {
                        "id": 2,
                        "first_name": "Vorname",
                        "last_name": "Nachname",
                        "organisation": "Organisation",
                        "location": "Location",
                    },
                    {
                        "id": 3,
                        "first_name": "Vorname",
                        "last_name": "Nachname",
                        "organisation": "Organisation",
                        "location": "Location",
                    },
                ]
            },
            {
                "id": 3,
                "name": "Topic of the coffee table",
                "image_url": "/path/to/image.png",
                "url": "https://bbb.wechange.de/b/mar-fq2-kud",
                "participants": [
                    {
                        "id": 1,
                        "first_name": "Vorname",
                        "last_name": "Nachname",
                        "organisation": "Organisation",
                        "location": "Location",
                    },
                    {
                        "id": 2,
                        "first_name": "Vorname",
                        "last_name": "Nachname",
                        "organisation": "Organisation",
                        "location": "Location",
                    },
                    {
                        "id": 3,
                        "first_name": "Vorname",
                        "last_name": "Nachname",
                        "organisation": "Organisation",
                        "location": "Location",
                    },
                ]
            },
        ])

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
