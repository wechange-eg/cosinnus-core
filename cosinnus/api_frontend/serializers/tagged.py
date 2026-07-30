import logging
import random

from django.contrib.auth import get_user_model
from geopy import OpenCage
from geopy.exc import GeocoderInsufficientPrivileges, GeopyError
from geopy.extra.rate_limiter import RateLimiter
from rest_framework import serializers

from cosinnus.conf import settings
from cosinnus.models import BaseTaggableObjectModel
from cosinnus.utils.functions import is_number
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.permissions import check_user_can_see_user
from cosinnus.views.common import apply_star_object

logger = logging.getLogger('cosinnus')


class CosinnusMediaTagSerializerMixin:
    """
    Mixin to serialize media tag.
    Usage:
    - Add needed media_tags fields to serializer with source.
    - Call save_media_tag in serializer create/update with the validated media_tag_data
    See CosinnusHybridUserSerializer for example usage.
    """

    def save_media_tag(self, media_tag, media_tag_data, locked_visibility=None, save=True):
        """
        Save validated media tag tag to media tag.
        @param media_tag: media_tag instance
        @param media_tag_data: validate media_tag_data
        @param locked_visibility: Force setting fixed visibility value ignoring visibility in media_tag_data
        @param save: Save the media_tag instance
        """
        # save visibility field to locked value or value from data
        if locked_visibility is not None:
            media_tag.visibility = locked_visibility
        else:
            media_tag.visibility = media_tag_data.get('visibility', media_tag.visibility)

        # save topics
        topics = media_tag_data.get('get_topic_ids', None)
        if topics is not None:
            media_tag.topics = ','.join([str(topic) for topic in topics])

        # save tags
        tags = media_tag_data.get('tags', None)
        if tags:
            media_tag.tags.set(*tags, clear=True)

        # save location
        if 'location' in media_tag_data:
            location_str = media_tag_data['location']
            location_lat = media_tag_data.get('location_lat', None)
            location_lon = media_tag_data.get('location_lon', None)
            if not location_str or not location_str.strip():
                # reset location
                media_tag.location = None
                media_tag.location_lat = None
                media_tag.location_lon = None
            elif location_lat and location_lon and is_number(location_lat) and is_number(location_lon):
                # if the location string and location_lat and location_lon coordinates are given, simply save them
                media_tag.location = location_str.strip()
                media_tag.location_lat = float(location_lat)
                media_tag.location_lon = float(location_lon)
            else:
                # save location string and clear coordinates
                media_tag.location = location_str
                media_tag.location_lat = None
                media_tag.location_lon = None

                # use OpenCage service to determine an actual location from the given string
                if settings.COSINNUS_GEOCODE_OPENCAGE_KEY:
                    geolocator = OpenCage(api_key=settings.COSINNUS_GEOCODE_OPENCAGE_KEY, timeout=5)
                    # retry max 10 times, after between 0.5 - 1 secs randomly
                    geocode = RateLimiter(
                        geolocator.geocode,
                        min_delay_seconds=0.5,
                        max_retries=10,
                        error_wait_seconds=0.5 + random.uniform(0.0, 0.5),
                    )

                    location = None
                    try:
                        location = geocode(location_str.strip())
                    except (GeocoderInsufficientPrivileges, GeopyError, Exception) as e:
                        extra = {
                            'media_tag_id': media_tag.id,
                            'location_str': location_str,
                            'reason': type(e),
                            'exc': str(e),
                        }
                        logger.error(
                            (
                                'Error: A user location could not be geoceded as nominatim, the request returned an '
                                'error! '
                            ),
                            extra=extra,
                        )
                    if location:
                        media_tag.location_lat = location.latitude
                        media_tag.location_lon = location.longitude
                else:
                    # no opencage api key defined, log a waning that the location str was not saved!
                    extra = {
                        'media_tag_id': media_tag.id,
                        'location_str': location_str,
                    }
                    logger.warning(
                        ('Warning: A user location could not be geoceded as nominatim as no geocode api key was set.'),
                        extra=extra,
                    )

        # save location_type
        if 'location_type' in media_tag_data:
            media_tag.location_type = media_tag_data['location_type']

        # save external_video_conference_url
        if 'external_video_conference_url' in media_tag_data:
            media_tag.external_video_conference_url = media_tag_data['external_video_conference_url']

        # save instance
        if save:
            media_tag.save()


class CosinnusTagObjectBookmarkSerializer(serializers.Serializer):
    """Serializer to handle bookmarking / starring of tagged objects."""

    bookmarked = serializers.BooleanField(required=True)

    def to_representation(self, instance):
        user = self.context['request'].user
        return {'bookmarked': instance.is_user_starring(user)}

    def update(self, instance, validated_data):
        user = self.context['request'].user
        apply_star_object(instance, user, star=validated_data['bookmarked'])
        return instance


class CosinnusTaggableObjectCreatorSerializer(serializers.ModelSerializer):
    """Readonly serializer for the taggable object creator."""

    name = serializers.CharField(source='cosinnus_profile.get_full_name', read_only=True)
    avatar = serializers.URLField(source='cosinnus_profile.get_avatar_thumbnail_url', read_only=True)
    profile_url = serializers.URLField(source='cosinnus_profile.get_absolute_url', read_only=True)

    class Meta:
        model = get_user_model()
        fields = (
            'name',
            'avatar',
            'profile_url',
        )

    def to_representation(self, instance):
        """Check view permissions for creator."""
        user = None
        if 'user' in self.context:
            user = self.context['user']
        if 'request' in self.context:
            user = self.context['request'].user
        if not user or not check_user_can_see_user(user, instance):
            return None
        return super().to_representation(instance)


class CosinnusTaggableObjectGroupSerializer(serializers.ModelSerializer):
    """Readonly serializer for the taggable object group."""

    url = serializers.URLField(source='get_absolute_url', read_only=True)

    class Meta(object):
        model = get_cosinnus_group_model()
        fields = ('name', 'url')


class CosinnusBaseTaggableObjectSerializer(serializers.ModelSerializer):
    """Readonly base serializer for taggable objects"""

    creator = CosinnusTaggableObjectCreatorSerializer(read_only=True)
    group = CosinnusTaggableObjectGroupSerializer(read_only=True)
    url = serializers.URLField(source='get_absolute_url', read_only=True)

    class Meta:
        model = BaseTaggableObjectModel
        fields = (
            'id',
            'title',
            'creator',
            'created',
            'group',
            'url',
        )
