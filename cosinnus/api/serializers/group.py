# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from datetime import datetime
import pytz
from django.db.models import Q
from rest_framework import serializers

from cosinnus.models import MEMBERSHIP_ADMIN, get_cosinnus_group_model, RelatedGroups

__all__ = ('GroupSimpleSerializer', 'CosinnusSocietySerializer', 'CosinnusProjectSerializer')

from cosinnus.models.group_extra import CosinnusSociety, CosinnusProject


CosinnusGroup = get_cosinnus_group_model()


class GroupSimpleSerializer(serializers.ModelSerializer):

    class Meta(object):
        model = CosinnusGroup
        fields = ('id', 'name', 'slug', 'public', 'description')


class CosinnusSocietySerializer(serializers.HyperlinkedModelSerializer):
    topics = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()
    locations = serializers.SerializerMethodField()
    related = serializers.SerializerMethodField()

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

    def get_related(self, obj):
        qs = RelatedGroups.objects
        slugs = set(qs.filter(from_group=obj).exclude(to_group=obj).values_list('to_group__slug', flat=True))
        slugs.update(set(qs.filter(to_group=obj).exclude(from_group=obj).values_list('from_group__slug', flat=True)))
        return slugs

    class Meta(object):
        model = CosinnusSociety
        fields = ('name', 'slug', 'description', 'description_long', 'contact_info',
                  'avatar', 'website', 'related', 'topics', 'tags', 'locations', 'created')


class CosinnusProjectSerializer(CosinnusSocietySerializer):
    parent = serializers.SlugRelatedField(queryset=CosinnusSociety.objects.all(), slug_field='slug', required=False)

    class Meta(CosinnusSocietySerializer.Meta):
        model = CosinnusProject
        fields = CosinnusSocietySerializer.Meta.fields + ('parent', )


class CosinnusLocationSerializer(serializers.HyperlinkedModelSerializer):
    description = serializers.CharField(source='location')
    geo = serializers.SerializerMethodField()

    class Meta(object):
        model = CosinnusProject
        fields = ('description', 'geo')

    def get_geo(self, obj):
        if obj and obj.location_lat and obj.location_lon:
            return {'latitude': obj.location_lat, 'longitude': obj.location_lat}
        return None


class CosinnusProjectGoodDBSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.URLField(source='get_absolute_url', read_only=True)
    createdAt = serializers.SerializerMethodField()
    placeType = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    coordinates = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    contact = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()
    tags = serializers.SerializerMethodField()

    class Meta(object):
        model = CosinnusProject
        fields = ('id', 'createdAt', 'name', 'description', 'placeType', 'images', 'coordinates', 'address', 'contact',
                  'categories', 'tags')

    def _get_unixtime(self, datetime_obj):
        epoch = datetime(1970, 1, 1, tzinfo=pytz.UTC)
        return int((datetime_obj - epoch).total_seconds())

    def get_createdAt(self, obj):
        return self._get_unixtime(obj.created)

    def get_coordinates(self, obj):
        locations = obj.get_locations()
        if len(locations) > 0:
            location = locations[0]
            return {
                'lat': location.location_lat,
                'lng': location.location_lon,
            }
        return {}

    def get_address(self, obj):
        return {}
        # {
        #     'street': self.street,
        #     'zip': self.zipcode,
        #     'city': self.city,
        #     'country': None,
        # }

    def get_contact(self, obj):
        contact = {}
        admins = obj.memberships.filter(status=MEMBERSHIP_ADMIN)
        contact['email'] = list(admins.values_list('user__email', flat=True))

        if obj.website:
            contact['websites'] = [obj.website]
        return contact

    def get_tags(self, obj):
        tags = []
        if hasattr(obj, 'media_tag'):
            tags = [t.name for t in obj.media_tag.tags.all()]
        return tags

    def get_categories(self, obj):
        categories = []
        if hasattr(obj, 'media_tag'):
            categories = obj.media_tag.get_topics()
        return categories

    def get_placeType(self, obj):
        return 'Project'

    def get_images(self, obj):
        images = []
        if hasattr(obj, 'avatar'):
            images = [{
                'url':   obj.avatar.url,
                'primary': True,
                'title': obj.avatar.name
            }]
        return images
