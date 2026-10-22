import logging
import random

from geopy import OpenCage
from geopy.exc import GeocoderInsufficientPrivileges, GeopyError
from geopy.extra.rate_limiter import RateLimiter

from cosinnus.conf import settings

logger = logging.getLogger('cosinnus')


def geocode_location(query, request=None, media_tag=None, exactly_one=True):
    """
    Uses the geocode api to get locations for a query string.
    @param query: Location  string.
    @param request: User request used to determine language. If not passed, settings.LANGUAGE_CODE is used.
    @param media_tag: Media_tag being updated, used for error logging only.
    @param exactly_one: If set only one result is returned, otherwise a list is returned.
    @return: ``None``, :class:`geopy.location.Location` or a list of them, if ``exactly_one=False``.
    """
    if not settings.COSINNUS_GEOCODE_OPENCAGE_KEY:
        logger.warning('Warning: A location could not be geoceded as nominatim, as no geocode api key was set.')
        return None
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
        language = request.LANGUAGE_CODE if request else settings.LANGUAGE_CODE
        location = geocode(query.strip(), language=language, annotations=False, exactly_one=exactly_one)
        if location and isinstance(location, list):
            # sort result list by confidence
            location = sorted(location, key=lambda loc: loc.raw['confidence'], reverse=True)
    except (GeocoderInsufficientPrivileges, GeopyError, Exception) as e:
        extra = {
            'query': query,
            'reason': type(e),
            'exc': str(e),
        }
        if media_tag:
            extra['media_tag_id'] = media_tag.id
        logger.error(
            'Error: A location could not be geoceded as nominatim, the request returned an error! ',
            extra=extra,
        )
    return location
