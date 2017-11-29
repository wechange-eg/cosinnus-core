# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import collections
import datetime
import json
import six
from operator import __or__ as OR, __and__ as AND

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.db.models import Q
from django.http.response import JsonResponse, HttpResponseBadRequest
from django.utils.encoding import force_text
from django.utils.timezone import now
from haystack.query import SearchQuerySet
from haystack.utils.geo import Point

from cosinnus.forms.search import filter_searchqueryset_for_read_access,\
    filter_searchqueryset_for_portal
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import CosinnusSociety, CosinnusProject
from cosinnus.models.profile import get_user_profile_model
from cosinnus.models.tagged import BaseTagObject
from cosinnus.utils.functions import is_number, ensure_list_of_ints
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user
from cosinnus.utils.user import filter_active_users


USER_MODEL = get_user_model()

# supported map search query parameters, and their default values (as python data after a json.loads()!) if not present
MAP_PARAMETERS = {
    'q': '', # search query, wildcard if empty
    'sw_lat': -90, # SW latitude, max southwest
    'sw_lon': -180, # SW longitude, max southwest
    'ne_lat': 90, # NE latitude, max northeast
    'ne_lon': 180, # NE latitude, max northeast
    'people': True,
    'events': True,
    'projects': True,
    'groups': True,
    'limit': 500, # result count limit, integer or None
    'topics': None,
}


SEARCH_MODEL_NAMES = {
    get_user_profile_model(): 'people',
    CosinnusProject: 'projects',
    CosinnusSociety: 'groups',
}
try:
    from cosinnus_event.models import Event
    SEARCH_MODEL_NAMES.update({
        Event: 'events',                           
    })
except:
    Event = None
    

def _better_json_loads(s):
    """ Can pass pure string values and None through without exception """
    if s is None:
        return None
    try:
        return json.loads(s)
    except ValueError, e:
        if isinstance(s, six.string_types):
            return s
        else:
            raise


def _collect_parameters(param_dict, parameter_list):
    """ For a GET/POST dict, collects all attributes listes as keys in ``parameter_list``.
        If not present in the GET/POST dict, the value of the key in ``parameter_list`` will be used. """
    results = {}
    for key, value in parameter_list.items():
        if key in param_dict:
            results[key] = _better_json_loads(param_dict.get(key, None))
        else:
            results[key] = value
    return results


class MapResult(dict):
    """ A single result for the search of the map, enforcing required fields """

    def __init__(self, lat, lon, address, title, url=None, imageUrl=None, description=None, *args, **kwargs):
        self['lat'] = lat
        self['lon'] = lon
        self['address'] = address
        self['title'] = title
        self['url'] = url
        self['imageUrl'] = imageUrl
        self['description'] = description
        return super(MapResult, self).__init__(*args, **kwargs)


class HaystackMapResult(MapResult):
    """ Takes a Haystack Search Result and funnels its properties (most data comes from ``StoredDataIndexMixin``)
         into a proper MapResult """

    def __init__(self, result, *args, **kwargs):
        return super(HaystackMapResult, self).__init__(
            result.mt_location_lat,
            result.mt_location_lon,
            result.mt_location,
            result.title, 
            result.url,
            result.marker_image_url,
            result.description,
        )


class MapSearchResults(dict):
    """ The return of a map search, containing lists of ``MapResult``, enforcing required sets of results """

    def __init__(self, people=[], events=[], projects=[], groups=[], *args, **kwargs):
        self['people'] = people
        self['events'] = events
        self['projects'] = projects
        self['groups'] = groups
        return super(MapSearchResults, self).__init__(*args, **kwargs)


def map_search_endpoint(request, filter_group_id=None):
    """ Maps API search endpoint using haystack search results. For parameters see ``MAP_PARAMETERS``
        returns JSON with the contents of type ``MapSearchResults``
        
        @param filter_group_id: Will filter all items by group relation, where applicable 
                (i.e. users are filtered by group memberships for that group, events as events in that group)
        """
    
    params = _collect_parameters(request.GET, MAP_PARAMETERS)
    query = force_text(params['q'])
    limit = params['limit']
    
    if not is_number(limit) or limit < 0:
            return HttpResponseBadRequest('``limit`` param must be a positive number or 0!')
    
    # filter for requested model types
    model_list = [klass for klass,param_name in SEARCH_MODEL_NAMES.items() if params[param_name]]
    sqs = SearchQuerySet().models(*model_list)
    # filter for map bounds (Points are constructed ith (lon, lat)!!!)
    sqs = sqs.within('location', Point(params['sw_lon'], params['sw_lat']), Point(params['ne_lon'], params['ne_lat']))
    # filter for search terms
    if query:
        sqs = sqs.auto_query(query)
    # group-filtered-map view for on-group pages
    if filter_group_id:
        sqs = sqs.filter_and(Q(membership_groups=filter_group_id) | Q(group=filter_group_id))
    # filter topics
    topics = ensure_list_of_ints(params.get('topics', ''))
    if topics: 
        sqs = sqs.filter_and(mt_topics__in=topics)
    # filter for portal visibility
    sqs = filter_searchqueryset_for_portal(sqs)
    # filter for read access by this user
    sqs = filter_searchqueryset_for_read_access(sqs, request.user)
    # filter events by upcoming status
    if params['events'] and Event is not None:
        _now = now()
        event_horizon = datetime.datetime(_now.year, _now.month, _now.day)
        sqs = sqs.exclude(Q(to_date__lt=event_horizon) | (Q(_missing_='to_date') & Q(from_date__lt=event_horizon)))
        
    # sort results into one list per model
    sqs = sqs[:limit]
    results = collections.defaultdict(list)
    for result in sqs:
        results[SEARCH_MODEL_NAMES[result.model]].append(HaystackMapResult(result))
    
    data = MapSearchResults(**results)
    return JsonResponse(data)

