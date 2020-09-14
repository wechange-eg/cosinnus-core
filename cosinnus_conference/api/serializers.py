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
        return [
            {'name': 'Lobby', 'slug': 'lobby', 'count': 56},
            {'name': 'Stage', 'slug': 'stage', 'count': 56},
            {'name': 'Discussions', 'slug': 'discussions', 'count': 56},
            {'name': 'Workshops', 'slug': 'workshops', 'count': 56},
            {'name': 'Coffee Tables', 'slug': 'coffee-tables', 'count': 56},
            {'name': 'Networking', 'slug': 'networking', 'count': 56},
            {'name': 'Exhibition', 'slug': 'exhibition', 'count': 56},
            {'name': 'Results', 'slug': 'results', 'count': 56},
        ]
