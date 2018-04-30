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
    filter_searchqueryset_for_portal, get_visible_portal_ids
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import CosinnusSociety, CosinnusProject
from cosinnus.models.profile import get_user_profile_model
from cosinnus.models.tagged import BaseTagObject
from cosinnus.utils.functions import is_number, ensure_list_of_ints
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user
from cosinnus.utils.user import filter_active_users
from cosinnus.templatetags.cosinnus_tags import textfield


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
    'limit': 20, # result count limit, integer or None
    'page': 0,
    'topics': None,
    'item': None,
    'ignore_location': False, # if True, we completely ignore locs, and even return results without location
}


SHORTENED_ID_MAP = {
    'cosinnus.cosinnusproject': 1,
    'cosinnus.cosinnussociety': 2,
    'cosinnus.userprofile': 3,
    'cosinnus_event.event': 4,
}

SEARCH_MODEL_NAMES = {
    get_user_profile_model(): 'people',
    CosinnusProject: 'projects',
    CosinnusSociety: 'groups',
}
SHORT_MODEL_MAP = {
    1: CosinnusProject,
    2: CosinnusSociety,
    3: get_user_profile_model(),
}
try:
    from cosinnus_event.models import Event
    SEARCH_MODEL_NAMES.update({
        Event: 'events',                           
    })
    SHORT_MODEL_MAP.update({
        4: Event,
    })
except:
    Event = None


def shorten_haystack_id(long_id):
    """ Shortens ids by replacing the <module.model> part of the id with a number. 
        Example: long_id 'cosinnus.userprofile.2' --> '3.2' """
    modulemodel, pk = long_id.rsplit('.', 1)
    short_id = '%d.%s' % (SHORTENED_ID_MAP[modulemodel], pk)
    return short_id

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


class BaseMapResult(dict):
    """ A single result for the search of the map, enforcing required fields """
    REQUIRED = object()
    
    fields = {
        'id': REQUIRED,
        'type': REQUIRED, 
        'title': REQUIRED, 
        'lat': None, 
        'lon': None, 
        'address': None, 
        'url': None,
        'iconImageUrl': None, 
        'backgroundImageSmallUrl': None,
        'backgroundImageLargeUrl': None,
        'description': None,
        'relevance': 0,
        'topics' : [], 
        'portal': None,
        'group_slug': None,
        'group_name': None,
        'participant_count': -1, # attendees for events, projects for groups
        'member_count': -1, # member count for projects/groups, group-member count for events, memberships for users
        'content_count': -1, # groups/projects: number of upcoming events
    }
    
    def __init__(self, *args, **kwargs):
        for key in self.fields.keys():
            val = kwargs.get(key, self.fields.get(key))
            if val == self.REQUIRED:
                raise Exception('MAP API Error: Expected required key "%s" for MapResult!' % key)
        return super(BaseMapResult, self).__init__(*args, **kwargs)


class HaystackMapResult(BaseMapResult):
    """ Takes a Haystack Search Result and funnels its properties (most data comes from ``StoredDataIndexMixin``)
         into a proper MapResult """

    def __init__(self, result, *args, **kwargs):
        if result.portals:
            # some results, like users, have multiple portals associated. we select one of those to show
            # the origin from
            visible_portals = get_visible_portal_ids()
            displayable_portals = [port_id for port_id in result.portals if port_id in visible_portals]
            current_portal_id = CosinnusPortal.get_current().id
            portal = current_portal_id if current_portal_id in displayable_portals else displayable_portals[0]
        else:
            portal = result.portal
        
        fields = {
            'id': shorten_haystack_id(result.id),
            'type': SEARCH_MODEL_NAMES[result.model],
            'title': result.title, 
            'lat': result.mt_location_lat,
            'lon': result.mt_location_lon,
            'address': result.mt_location,
            'url': result.url,
            'iconImageUrl': result.icon_image_url,
            'backgroundImageSmallUrl': result.background_image_small_url,
            'backgroundImageLargeUrl': result.background_image_large_url,
            'description': textfield(result.description),
            'relevance': result.score,
            'topics': result.mt_topics,
            'portal': portal,
            'group_slug': result.group_slug,
            'group_name': result.group_name,
            'participant_count': result.participant_count,
            'member_count': result.member_count,
            'content_count': result.content_count,
        }
        fields.update(**kwargs)
        
        return super(HaystackMapResult, self).__init__(*args, **fields)



def map_search_endpoint(request, filter_group_id=None):
    """ Maps API search endpoint using haystack search results. For parameters see ``MAP_PARAMETERS``
        returns JSON with the contents of type ``MapSearchResults``
        
        @param filter_group_id: Will filter all items by group relation, where applicable 
                (i.e. users are filtered by group memberships for that group, events as events in that group)
        """
    params = _collect_parameters(request.GET, MAP_PARAMETERS)
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
