# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from rest_framework import serializers

from cosinnus.models.group import CosinnusGroup


__all__ = ('ConferenceSerializer', )


class ConferenceSerializer(serializers.HyperlinkedModelSerializer):
    rooms = serializers.SerializerMethodField()

    class Meta(object):
        model = CosinnusGroup
        fields = ('name', 'description', 'rooms')

    def get_rooms(self, obj):
        return {
            'lobby': {'name': 'Lobby', 'type': 'lobby', 'count': 56, 'url': 'https://chat.wechange.de/group/developers'},
            'stage': {'name': 'Stage', 'type': 'stage', 'count': 56, 'url': 'https://chat.wechange.de/group/developers'},
            'discussions': {'name': 'Discussions', 'type': 'discussions', 'count': 56, 'url': 'https://chat.wechange.de/group/developers'},
            'workshops': {'name': 'Workshops', 'type': 'workshops', 'count': 56, 'url': 'https://chat.wechange.de/group/developers'},
            'coffee-tables': {'name': 'Coffee Tables', 'type': 'coffee-tables', 'count': 56, 'url': 'https://chat.wechange.de/group/developers'},
            'networking': {'name': 'Networking', 'type': 'networking', 'count': 56, 'url': 'https://chat.wechange.de/group/developers'},
            'exhibition': {'name': 'Exhibition', 'type': 'exhibition', 'count': 56, 'url': 'https://chat.wechange.de/group/developers'},
            'results': {'name': 'Results', 'type': 'results', 'count': 56, 'url': 'http://dina.localhost:8000/project/testprojekt/'},
        }
