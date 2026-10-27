from cosinnus.utils.map import map_search


def get_external_resources(user):
    """Helper to get external resouces from the map search, as used by the dashboard widget."""
    return map_search(user, externalresources=True, exchange=True, ignore_location=True)
