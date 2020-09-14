# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from rest_framework import serializers

from cosinnus.models.group import CosinnusGroup


__all__ = ('GroupSimpleSerializer', 'CosinnusSocietySerializer', 'CosinnusProjectSerializer')

from cosinnus.models.group_extra import CosinnusSociety, CosinnusProject


class GroupSimpleSerializer(serializers.ModelSerializer):

    class Meta(object):
        model = CosinnusGroup
        fields = ('id', 'name', 'slug', 'public', 'description', )


class CosinnusSocietySerializer(serializers.HyperlinkedModelSerializer):
    topics = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    locations = serializers.SerializerMethodField()
    parent = serializers.PrimaryKeyRelatedField(read_only=True)
    related_groups = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    def get_topics(self, obj):
        return obj.media_tag.get_topics()

    def get_tags(self, obj):
        return obj.media_tag.tags.values_list('name', flat=True)

    def get_locations(self, obj):
        locations = []
        for location in obj.get_locations():
            locations.append({
                'location': location.location,
                'lat': location.location_lat,
                'lon': location.location_lat,
                'url': location.location_url
            })
        return locations

    class Meta(object):
        model = CosinnusSociety
        fields = ('name', 'slug', 'description', 'description_long', 'contact_info',
                  'avatar', 'website', 'parent', 'related_groups', 'topics', 'tags', 'locations', 'created')


class CosinnusProjectSerializer(CosinnusSocietySerializer):
    class Meta(CosinnusSocietySerializer.Meta):
        model = CosinnusProject
