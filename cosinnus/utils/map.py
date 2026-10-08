from urllib.parse import quote

from django.urls import reverse

from cosinnus.conf import settings
from cosinnus.views.map_api import MAP_CONTENT_TYPE_SEARCH_PARAMETERS


def get_map_url_with_selected_filter_params(
    selected_search_model_names, topics=None, ignore_location=False, exchange=False
):
    """
    Utility function to get the map url with filter parameters with only some filters selected.
    Additionally, accepts topics to add to the url.
    E.g. get_get_map_selected_filter_params(["groups", "projects"]) returns filter parameters with only groups=true and
    projects=true and all other search model filters to false.
    :param selected_search_model_names: List of search model names.
    :param topics: String with comma separated topics added as the topics parameter
    :param ignore_location: Add ignore location parameter
    :param exchange: Set exchange search parameter
    """
    search_params = ''
    for parameter in list(MAP_CONTENT_TYPE_SEARCH_PARAMETERS):
        filter_setting = str(parameter in selected_search_model_names).lower()
        if search_params:
            search_params += '&'
        search_params += f'{parameter}={filter_setting}'
    map_url = reverse('cosinnus:map') + f'?{search_params}'
    if topics:
        map_url += f'&topics={quote(topics)}'
    if ignore_location:
        map_url += f'&ignore_location={str(ignore_location).lower()}'
    if settings.COSINNUS_EXCHANGE_ENABLED:
        map_url += f'&exchange={str(exchange).lower()}'
    return map_url
