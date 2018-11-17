from builtins import object
from rest_framework import serializers

from cosinnus.models.group_extra import CosinnusSociety, CosinnusProject
from cosinnus.models.tagged import BaseTagObject


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


class OrganisationListSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.URLField(source='get_absolute_url', read_only=True)
    timestamp = serializers.DateTimeField(source='last_modified')

    class Meta(object):
        model = CosinnusProject
        fields = ('id', 'timestamp')


class CosinnusLocationSerializer(serializers.HyperlinkedModelSerializer):
    description = serializers.CharField(source='location')
    geo = serializers.SerializerMethodField()

    class Meta(object):
        model = CosinnusProject
        fields = ('description', 'geo')

    def get_geo(self, obj):
        if obj and obj.lat and obj.lon:
            return {'latitude': obj.lat, 'longitude': obj.lon}
        return None


class OrganisationRetrieveSerializer(serializers.HyperlinkedModelSerializer):
    id = serializers.URLField(source='get_absolute_url', read_only=True)
    timestamp = serializers.DateTimeField(source='last_modified')
    slogan = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()
    admins = serializers.SerializerMethodField()
    locations = CosinnusLocationSerializer(many=True)

    def get_slogan(self, obj):
        return ''

    def get_categories(self, obj):
        return obj.media_tag.get_topics()

    def get_admins(self, obj):
        queryset = obj.actual_admins
        # Show only public admins
        queryset = queryset.filter(cosinnus_profile__media_tag__visibility=BaseTagObject.VISIBILITY_ALL)
        return queryset.values_list('email', flat=True)

    class Meta(object):
        model = CosinnusProject
        fields = ('id', 'timestamp', 'name', 'slogan', 'description', 'website', 'categories', 'admins', 'locations')
