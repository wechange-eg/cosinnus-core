import logging
import random

from geopy import OpenCage
from geopy.exc import GeocoderInsufficientPrivileges, GeopyError
from geopy.extra.rate_limiter import RateLimiter

from cosinnus.conf import settings
from cosinnus.utils.functions import is_number

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
        if topics:
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
            elif settings.COSINNUS_GEOCODE_OPENCAGE_KEY:
                # use OpenCage service to determine an actual location from the given string
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
                            'Error: A user location could not be geoceded as nominatim, the request returned an error! '
                            'User location was not saved.'
                        ),
                        extra=extra,
                    )
                if location:
                    media_tag.location = location_str
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
