from urllib.parse import quote

from django.http.request import HttpRequest
from django.urls import reverse

from cosinnus.conf import settings
from cosinnus.views.map_api import MAP_CONTENT_TYPE_SEARCH_PARAMETERS, map_search_endpoint


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


def map_search(
    user,
    query=None,
    people=False,
    events=False,
    projects=False,
    groups=False,
    ideas=False,
    conferences=False,
    externalresources=False,
    cloudfiles=False,
    ignore_location=False,
    exchange=False,
    managed_tags=None,
    limit=None,
    **search_params,
):
    """
    Make an internal request to the map api.
    :param user: Request user.
    :param query: Search query.
    :param people: Search for users.
    :param events: Search for events.
    :param projects: Search projects.
    :param groups: Search groups.
    :param ideas: Search ideas.
    :param conferences: Search conferences.
    :param externalresources: Search external resources.
    :param cloudfiles: Search cloud files.
    :param ignore_location: Include search results without location.
    :param exchange: Include search results from exchange data.
    :param managed_tags: (list) Limit search to managed tags.
    :param limit: (int) Custom limit for the search, default limit (20) is used otherwise. Disabling limit is currently
                  not possible.
    :param search_params: Further search parameter overwrites.
    :return: lHaystackMapResult
    """
    request = HttpRequest()
    request.method = 'GET'
    request.user = user
    if query:
        request.GET['q'] = query
    request.GET['people'] = str(people).lower()
    request.GET['events'] = str(events).lower()
    request.GET['projects'] = str(projects).lower()
    request.GET['groups'] = str(groups).lower()
    request.GET['ideas'] = str(ideas).lower()
    request.GET['conferences'] = str(conferences).lower()
    request.GET['externalresources'] = str(externalresources).lower()
    request.GET['cloudfiles'] = str(cloudfiles).lower()
    request.GET['exchange'] = str(exchange).lower()
    request.GET['ignore_location'] = str(ignore_location).lower()
    if managed_tags:
        request.GET['managed_tags'] = ','.join(mt.id for mt in managed_tags)
    if limit:
        request.GET['limit'] = str(limit)
    for search_param in search_params:
        request.GET['search_param'] = str(search_param).lower()
    response = map_search_endpoint(request, skip_limit_backend=True)
    results = response.data.get('results')
    return results
