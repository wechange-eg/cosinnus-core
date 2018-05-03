# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import json

from annoying.functions import get_object_or_None
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http.response import JsonResponse, HttpResponseBadRequest, \
    HttpResponseNotFound, HttpResponseForbidden
from django.utils.encoding import force_text
from django.utils.timezone import now
from haystack.query import SearchQuerySet
from haystack.utils.geo import Point
import six

from cosinnus.forms.search import filter_searchqueryset_for_read_access, \
    filter_searchqueryset_for_portal
from cosinnus.models.map import HaystackMapResult, \
    SEARCH_MODEL_NAMES, SEARCH_MODEL_NAMES_REVERSE, \
    SEARCH_RESULT_DETAIL_TYPE_MAP, SHORT_MODEL_MAP
from cosinnus.models.profile import get_user_profile_model
from cosinnus.utils.functions import is_number, ensure_list_of_ints
from cosinnus.utils.permissions import check_object_read_access


try:
    from cosinnus_event.models import Event #noqa
except:
    Event = None

USER_MODEL = get_user_model()


def _better_json_loads(s):
    """ Can pass pure string values and None through without exception """
    if s is None:
        return None
    try:
        return json.loads(s)
    except ValueError:
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


# supported map search query parameters, and their default values (as python data after a json.loads()!) if not present
MAP_SEARCH_PARAMETERS = {
    'q': '', # search query, wildcard if empty
    'sw_lat': -90, # SW latitude, max southwest
    'sw_lon': -180, # SW longitude, max southwest
    'ne_lat': 90, # NE latitude, max northeast
    'ne_lon': 180, # NE latitude, max northeast
    'people': True,
    'events': True,
    'projects': True,
    'groups': True,
    'limit': 20, # result count limit, integer or None
    'page': 0,
    'topics': None,
    'item': None,
    'ignore_location': False, # if True, we completely ignore locs, and even return results without location
}


def map_search_endpoint(request, filter_group_id=None):
    """ Maps API search endpoint using haystack search results. For parameters see ``MAP_SEARCH_PARAMETERS``
        returns JSON with the contents of type ``HaystackMapResult``
        
        @param filter_group_id: Will filter all items by group relation, where applicable 
                (i.e. users are filtered by group memberships for that group, events as events in that group)
    """
    params = _collect_parameters(request.GET, MAP_SEARCH_PARAMETERS)
    query = force_text(params['q'])
    limit = params['limit']
    page = params['page']
    item_id = params['item']
    
    if not is_number(limit) or limit < 0:
        return HttpResponseBadRequest('``limit`` param must be a positive number or 0!')
    if not is_number(page) or page < 0:
        return HttpResponseBadRequest('``page`` param must be a positive number or 0!')
    
    # filter for requested model types
    model_list = [klass for klass,param_name in SEARCH_MODEL_NAMES.items() if params[param_name]]
    sqs = SearchQuerySet().models(*model_list)
    # filter for map bounds (Points are constructed ith (lon, lat)!!!)
    if not params['ignore_location']:
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
    
    # if we hae no query-boosted results, use *only* our custom sorting (haystack's is very random)
    if not query:
        sqs = sqs.order_by('-local_boost')
        
    # sort results into one list per model
    total_count = sqs.count()
    sqs = sqs[limit*page:limit*(page+1)]
    results = []
    for result in sqs:
        # if we hae no query-boosted results, use *only* our custom sorting (haystack's is very random)
        if not query:
            result.score = result.local_boost
        results.append(HaystackMapResult(result))
        
    # if the requested item (direct select) is not in the queryset snippet
    # (might happen because of an old URL), then mix it in as first item and drop the last
    if item_id:
        item_id = str(item_id)
        if not any([res['id'] == item_id for res in results]):
            item_result = get_searchresult_by_itemid(item_id)
            if item_result:
                results = [item_result] + results[:-1]
        
    page_obj = None
    if results:
        page_obj = {
            'index': page,
            'count': len(results),
            'total_count': total_count,
            'start': (limit * page) + 1,
            'end': (limit * page) + len(results),
            'has_next': total_count > (limit * (page + 1)),
            'has_previous': page > 0,
        }
    
    data = {
        'results': results,
        'page': page_obj,
    }
    return JsonResponse(data)


MAP_DETAIL_PARAMETERS = {
    'portal': -1, # portal id, < 0 means current
    'slug': '',# object slug
    'type': '', # item type, as defined in `SEARCH_MODEL_NAMES`
}


def map_detail_endpoint(request):
    """ Maps API object detail endpoint using pSQL results. For parameters see ``MAP_DETAIL_PARAMETERS``
        returns JSON with the contents of type ``DetailedMapResult``
    """
    params = _collect_parameters(request.GET, MAP_DETAIL_PARAMETERS)
    portal = params['portal']
    slug = params['slug']
    model_type = params['type']
    
    if not is_number(portal) or portal < -1:
        return HttpResponseBadRequest('``portal`` param must be a positive number!')
    if not slug:
        return HttpResponseBadRequest('``slug`` param must be supplied!')
    if not model_type or not isinstance(model_type, six.string_types):
        return HttpResponseBadRequest('``type`` param must be supplied and be a string!')
    
    # try to retrieve the requested object
    model = SEARCH_MODEL_NAMES_REVERSE.get(model_type, None)
    if model is None:
        return HttpResponseBadRequest('``type`` param indicated an invalid data model type!')
    
    if model == get_user_profile_model():
        obj = get_object_or_None(get_user_model(), user__username=slug, cosinnus_portal_memberships=portal)
    else:
        obj = get_object_or_None(model, portal_id=portal, slug=slug)
    if obj is None:
        return HttpResponseNotFound('No item found that matches the requested type and slug.')
    
    # check read permission
    if not check_object_read_access(obj, request.user):
        return HttpResponseForbidden('You do not have permission to access this item.')
    
    # format data
    result_model = SEARCH_RESULT_DETAIL_TYPE_MAP[model_type]
    result = result_model(obj)
    
    data = {
        'result': result,
    }
    return JsonResponse(data)
    

def get_searchresult_by_itemid(item_id):
    """ Retrieves a HaystackMapResult just as the API would, for a given shortid
        in the form of `<classid>.<instanceid>` (see `shorten_haystack_id()`). """
        
    item_id = str(item_id)
    model_type, model_id = item_id.split('.')
    model_class = SHORT_MODEL_MAP[int(model_type)]
    smallsqs = SearchQuerySet().models(model_class).filter(id=int(model_id))
    if len(smallsqs) > 0:
        return HaystackMapResult(smallsqs[0])
    return None
