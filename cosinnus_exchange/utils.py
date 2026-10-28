from cosinnus.conf import settings
from cosinnus.utils.map import map_search


def get_external_resources(user):
    """Helper to get external resources from the map search, as used by the dashboard widget."""
    if not settings.COSINNUS_EXCHANGE_ENABLED or not settings.COSINNUS_EXCHANGE_EXTERNAL_RESOURCES_ENABLED:
        return None
    return map_search(user, externalresources=True, exchange=True, ignore_location=True)
