from geopy.geocoders.osm import Nominatim

from cosinnus.utils.functions import is_number


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
            else:
                # use nominatim service to determine an actual location from the given string
                # TODO: extract nominatim URL and use ours for production!
                geolocator = Nominatim(domain='nominatim.openstreetmap.org', user_agent='wechange')
                location = geolocator.geocode(location_str.strip(), timeout=5)
                if location:
                    media_tag.location = location_str
                    media_tag.location_lat = location.latitude
                    media_tag.location_lon = location.longitude

        # save instance
        if save:
            media_tag.save()
