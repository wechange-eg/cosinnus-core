# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
import json
import logging

from annoying.functions import get_object_or_None
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone
from django.http.response import JsonResponse, HttpResponseBadRequest, \
    HttpResponseNotFound, HttpResponseForbidden
from django.utils.encoding import force_text
from haystack.query import SearchQuerySet
from haystack.utils.geo import Point
import six

from cosinnus.conf import settings
from cosinnus.forms.search import filter_searchqueryset_for_read_access, \
    filter_searchqueryset_for_portal
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.map import CloudfileMapCard, HaystackMapResult, \
    SEARCH_MODEL_NAMES, SEARCH_MODEL_NAMES_REVERSE, \
    SEARCH_RESULT_DETAIL_TYPE_MAP, \
    SEARCH_MODEL_TYPES_ALWAYS_READ_PERMISSIONS, \
    filter_event_searchqueryset_by_upcoming, \
    filter_event_or_conference_starts_after, \
    filter_event_or_conference_starts_before
from cosinnus.models.profile import get_user_profile_model
from cosinnus.utils.functions import is_number, ensure_list_of_ints
from cosinnus.utils.permissions import check_object_read_access
from django.utils.html import escape
from cosinnus.utils.group import get_cosinnus_group_model,\
    get_default_user_group_slugs


try:
    from cosinnus_event.models import Event #noqa
except:
    Event = None

USER_MODEL = get_user_model()
logger = logging.getLogger('cosinnus')

SERVER_SIDE_SEARCH_LIMIT = 200


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
    for key, value in list(parameter_list.items()):
        if key in param_dict:
            results[key] = _better_json_loads(param_dict.get(key, None))
        else:
            results[key] = value
    return results

# supported map search query parameters, and their default values (as python data after a json.loads()!) if not present
MAP_NON_CONTENT_TYPE_SEARCH_PARAMETERS = {
    'q': '', # search query, wildcard if empty
    'sw_lat': -90, # SW latitude, max southwest
    'sw_lon': -180, # SW longitude, max southwest
    'ne_lat': 90, # NE latitude, max northeast
    'ne_lon': 180, # NE latitude, max northeast
    'limit': 20, # result count limit, integer or None
    'page': 0,
    'topics': None,
    'text_topics': None,
    'item': None,
    'ignore_location': False, # if True, we completely ignore locs, and even return results without location
    'mine': False, # if True, we only show items of the current user. ignored if user not authenticated
    'external': False,
    'fromDate': None,
    'fromTime': None,
    'toDate': None,
    'toTime': None,
    'exchange': False,
}
# supported map search query parameters for selecting content models, and their default values (as python data after a json.loads()!) if not present
MAP_CONTENT_TYPE_SEARCH_PARAMETERS = {
    'people': True,
    'events': True,
    'projects': True,
    'groups': True,
}

if settings.COSINNUS_MANAGED_TAGS_ENABLED:
    MAP_CONTENT_TYPE_SEARCH_PARAMETERS.update({
        'managed_tags': None,
    })
if settings.COSINNUS_ENABLE_SDGS:
    MAP_CONTENT_TYPE_SEARCH_PARAMETERS.update({
        'sdgs': None,
    })
if settings.COSINNUS_IDEAS_ENABLED:
    MAP_CONTENT_TYPE_SEARCH_PARAMETERS.update({
        'ideas': True,
    })
if settings.COSINNUS_ORGANIZATIONS_ENABLED:
    MAP_CONTENT_TYPE_SEARCH_PARAMETERS.update({
        'organizations': True,
    })
if settings.COSINNUS_CONFERENCES_ENABLED:
    MAP_CONTENT_TYPE_SEARCH_PARAMETERS.update({
        'conferences': True,
    })
if settings.COSINNUS_CLOUD_ENABLED:
    MAP_CONTENT_TYPE_SEARCH_PARAMETERS.update({
        'cloudfiles': True,
    })

# supported map search query parameters, and their default values (as python data after a json.loads()!) if not present
MAP_SEARCH_PARAMETERS = {}
MAP_SEARCH_PARAMETERS.update(MAP_NON_CONTENT_TYPE_SEARCH_PARAMETERS)
MAP_SEARCH_PARAMETERS.update(MAP_CONTENT_TYPE_SEARCH_PARAMETERS)



def map_search_endpoint(request, filter_group_id=None):
    """ Maps API search endpoint using haystack search results. For parameters see ``MAP_SEARCH_PARAMETERS``
        returns JSON with the contents of type ``HaystackMapResult``
        
        @param filter_group_id: Will filter all items by group relation, where applicable 
                (i.e. users are filtered by group memberships for that group, events as events in that group)
    """
    implicit_ignore_location = not any([loc_param in request.GET for loc_param in ['sw_lon', 'sw_lat', 'ne_lon', 'ne_lat']])
    params = _collect_parameters(request.GET, MAP_SEARCH_PARAMETERS)
    query = force_text(params['q'])
    limit = params['limit']
    page = params['page']
    item_id = params['item']
    
    if params.get('cloudfiles', False):
        return map_cloudfiles_endpoint(request, query, limit, page)

    if not settings.COSINNUS_EXCHANGE_ENABLED:
        params['exchange'] = False
    
    prefer_own_portal = getattr(settings, 'MAP_API_HACKS_PREFER_OWN_PORTAL', False)
    
    if not is_number(limit) or limit < 0:
        return HttpResponseBadRequest('``limit`` param must be a positive number or 0!')
    limit = min(limit, SERVER_SIDE_SEARCH_LIMIT)
    if not is_number(page) or page < 0:
        return HttpResponseBadRequest('``page`` param must be a positive number or 0!')
    
    # filter for requested model types
    model_list = [klass for klass, param_name in list(SEARCH_MODEL_NAMES.items()) if params.get(param_name, False)]
        
    sqs = SearchQuerySet().models(*model_list)
    
    # filter for map bounds (Points are constructed ith (lon, lat)!!!)
    if not params['ignore_location'] and not implicit_ignore_location:
        sqs = sqs.within('location', Point(params['sw_lon'], params['sw_lat']), Point(params['ne_lon'], params['ne_lat']))
    # filter for user's own content
    if params['mine'] and request.user.is_authenticated:
        user_id = request.user.id
        sqs = sqs.filter_and(Q(creator=user_id) | Q(user_id=user_id) | Q(group_members=user_id))
    # filter for search terms
    if query:
        sqs = sqs.auto_query(query)
    
    # group-filtered-map view for on-group pages
    if filter_group_id:
        group = get_object_or_None(get_cosinnus_group_model(), id=filter_group_id)
        if group:
            filtered_groups = [filter_group_id]
            # get child projects of this group
            filtered_groups += [subproject.id for subproject in group.get_children() if subproject.is_active]
            sqs = sqs.filter_and(Q(membership_groups__in=filtered_groups) | Q(group__in=filtered_groups))
            
    # filter topics
    topics = ensure_list_of_ints(params.get('topics', ''))
    if topics:
        sqs = sqs.filter_and(mt_topics__in=topics)

    text_topics = ensure_list_of_ints(params.get('text_topics', ''))
    if text_topics:
        sqs = sqs.filter_and(mt_text_topics__in=text_topics)

    if settings.COSINNUS_ENABLE_SDGS:
        sdgs = ensure_list_of_ints(params.get('sdgs', ''))
        if sdgs:
            sqs = sqs.filter_and(sdgs__in=sdgs)
    if settings.COSINNUS_MANAGED_TAGS_ENABLED:
        managed_tags = ensure_list_of_ints(params.get('managed_tags', ''))
        if managed_tags:
            sqs = sqs.filter_and(managed_tags__in=managed_tags)
    # filter for portal visibility
    sqs = filter_searchqueryset_for_portal(sqs, restrict_multiportals_to_current=prefer_own_portal,
                                           exchange=params.get('exchange', False))
    # filter for read access by this user
    sqs = filter_searchqueryset_for_read_access(sqs, request.user)
    # filter events by upcoming status and exclude hidden proxies
    if params['events'] or params['conferences'] and Event is not None:
        sqs = filter_event_searchqueryset_by_upcoming(sqs).exclude(is_hidden_group_proxy=True)

    params_keys = [key for key, value in params.items() if value]
    settings_keys = MAP_CONTENT_TYPE_SEARCH_PARAMETERS.keys()

    content_type_params =  list(set(params_keys) & set(settings_keys))
    check_date_cts = ['events', 'conferences']
    reduced_pramas = list(set(content_type_params) & set(check_date_cts))

    check_date_by_date_param = params.get('fromDate') or params.get('toDate')
    check_date_by_conten_type = len(content_type_params) == len(reduced_pramas)

    if check_date_by_date_param and check_date_by_conten_type:
        from_date_string = params.get('fromDate')
        from_time_string = params.get('fromTime')
        to_date_string = params.get('toDate')
        to_time_string = params.get('toTime')

        sqs = filter_event_or_conference_starts_after(from_date_string, from_time_string, sqs)
        sqs = filter_event_or_conference_starts_before(to_date_string, to_time_string, sqs)

    # filter all default user groups if the new dashboard is being used (they count as "on plattform" and aren't shown)
    if getattr(settings, 'COSINNUS_USE_V2_DASHBOARD', False):
        sqs = sqs.exclude(is_group_model=True, slug__in=get_default_user_group_slugs())
    
    # kip score sorting and only rely on natural ordering?
    skip_score_sorting = False
    # if we hae no query-boosted results, use *only* our custom sorting (haystack's is very random)
    if not query:
        sort_args = ['-local_boost']
        # if we only look at conferences, order them by their from_date, future first!
        if prefer_own_portal:
            sort_args = ['-portal'] + sort_args
        
        """
        # this would be the way to force-sort a content type by a natural ordering instead of score if its the only type being shown
        if params.get('conferences', False) and sum([1 if params.get(content_key, False) else 0 for content_key in MAP_CONTENT_TYPE_SEARCH_PARAMETERS.keys()]) == 1:
            sort_args = ['-from_date'] + sort_args
            skip_score_sorting = True
        sqs = sqs.order_by(*sort_args)
        """
    
    # sort results into one list per model
    total_count = sqs.count()
    sqs = sqs[limit*page:limit*(page+1)]
    results = []
        
    for i, result in enumerate(sqs):
        if skip_score_sorting:
            # if we skip score sorting and only rely on the natural ordering, we make up fake high scores
            result.score = 100000 - (limit*page) - i
        elif not query:
            # if we hae no query-boosted results, use *only* our custom sorting (haystack's is very random)
            result.score = result.local_boost
            if prefer_own_portal and is_number(result.portal) and int(result.portal) == CosinnusPortal.get_current().id:
                result.score += 100.0
        results.append(HaystackMapResult(result, user=request.user))
        
    # if the requested item (direct select) is not in the queryset snippet
    # (might happen because of an old URL), then mix it in as first item and drop the last
    if item_id:
        item_id = str(item_id)
        if not any([res['id'] == item_id for res in results]):
            item_result = get_searchresult_by_itemid(item_id, request.user)
            if item_result:
                results = [HaystackMapResult(item_result, user=request.user)] + results[:-1]
        
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


def map_cloudfiles_endpoint(request, query, limit, page):
    from cosinnus_cloud.utils.nextcloud import perform_fulltext_search
    from cosinnus_cloud.hooks import get_nc_user_id

    result = perform_fulltext_search(get_nc_user_id(request.user), query, page=page+1, page_size=limit)

    if result['documents']:
        total_count = result['meta']['total']
        count = result['meta']['count']
        page_obj = {
            'index': page,
            'count': count,
            'total_count': total_count,
            'start': (limit * page) + 1,
            'end': (limit * page) + count,
            'has_next': total_count > (limit * (page + 1)),
            'has_previous': page > 0,
        }
    else:
        page_obj = None

    return JsonResponse({
        "results": [CloudfileMapCard(doc, query) for doc in result["documents"]],
        "page": page_obj
    })


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
    
    if not is_number(portal) or portal < 0:
        return HttpResponseBadRequest('``portal`` param must be a positive number!')
    if not slug:
        return HttpResponseBadRequest('``slug`` param must be supplied!')
    slug = force_text(slug) # stringify is necessary for number-only slugs
    if not model_type or not isinstance(model_type, six.string_types):
        return HttpResponseBadRequest('``type`` param must be supplied and be a string!')
    
    if portal == 0:
        portal = CosinnusPortal.get_current().id
    
    # try to retrieve the requested object
    model = SEARCH_MODEL_NAMES_REVERSE.get(model_type, None)
    if model is None:
        return HttpResponseBadRequest('``type`` param indicated an invalid data model type!')
    
    # for internal DB based objects:
    if portal != settings.COSINNUS_EXCHANGE_PORTAL_ID:
        # TODO: for groups/projects we should really use the cache here.
        if model_type == 'people':
            # UserProfiles are retrieved independent of the portal
            obj = get_object_or_None(get_user_profile_model(), user__username=slug)
        elif model_type == 'events':
            group_slug, event_slug = slug.split('*', 1)
            obj = get_object_or_None(model, group__portal__id=portal, group__slug=group_slug, slug=event_slug)
        else:
            obj = get_object_or_None(model, portal__id=portal, slug=slug)
        if obj is None:
            return HttpResponseNotFound('No item found that matches the requested type and slug (obj: %s, %s, %s).' % (escape(force_text(model)), portal, slug))
        
        # check read permission
        if not model_type in SEARCH_MODEL_TYPES_ALWAYS_READ_PERMISSIONS and not check_object_read_access(obj, request.user):
            return HttpResponseForbidden('You do not have permission to access this item.')
        # get the basic result data from the search index (as it is already prepared and faster to access there)
        haystack_result = get_searchresult_by_args(portal, model_type, slug)
        if not haystack_result:
            return HttpResponseNotFound('No item found that matches the requested type and slug (index: %s, %s, %s).' % (portal, model_type, slug))
        # format data
        result_model = SEARCH_RESULT_DETAIL_TYPE_MAP[model_type]
        result = result_model(haystack_result, obj, request.user, request=request)
    else:
        # for external, api based objects:
        haystack_result = get_searchresult_by_args(portal, model_type, slug)
        if not haystack_result:
            return HttpResponseNotFound('No item found that matches the requested type and slug (external: %s, %s, %s).' % (portal, model_type, slug))
        result = HaystackMapResult(haystack_result, request.user, request=request)
    
    data = {
        'result': result,
    }
    return JsonResponse(data)


def get_searchresult_by_itemid(itemid, user=None):
    portal, model_type, slug = itemid.split('.', 2)
    return get_searchresult_by_args(portal, model_type, slug, user=user)


def get_searchresult_by_args(portal, model_type, slug, user=None):
    """ Retrieves a HaystackMapResult just as the API would, for a given shortid
        in the form of `<classid>.<instanceid>` (see `itemid_from_searchresult()`). """
    
    # monkey-hack: if the portal id is 0, we have an external item, so look up the external models
    if settings.COSINNUS_EXCHANGE_ENABLED and portal == settings.COSINNUS_EXCHANGE_PORTAL_ID:
        from cosinnus.models.map import EXCHANGE_SEARCH_MODEL_NAMES_REVERSE
        model = EXCHANGE_SEARCH_MODEL_NAMES_REVERSE.get(model_type, None)
    else:
        model = SEARCH_MODEL_NAMES_REVERSE.get(model_type, None)
    
    if model_type == 'people':
        sqs = SearchQuerySet().models(model).filter_and(slug=slug)
    elif model_type == 'events':
        group_slug, slug = slug.split('*', 1)
        sqs = SearchQuerySet().models(model).filter_and(portal=portal, group_slug=group_slug, slug=slug)
    else:
        sqs = SearchQuerySet().models(model).filter_and(portal=portal, slug=slug)
    if user:
        # filter for read access by this user
        sqs = filter_searchqueryset_for_read_access(sqs, user)
    
    # hack: haystack seems to be unable to filter *exact* on `slug` (even when using __exact). 
    # this affects slugs like `my-slug` vs `my-slug-2`.
    # so we manually post-filter on slug to get an exact match
    if len(sqs) > 1:
        sqs = [result for result in sqs if result.slug == slug]
    
    if len(sqs) != 1:
        logger.warn('Got a DetailMap request where %d indexed results were found!' % len(sqs), extra={
            'portal': portal,
            'model': model,
            'slug': slug,
        })
        return None
    return sqs[0]
