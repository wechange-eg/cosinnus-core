# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import logging
import re
from builtins import str

import six
from annoying.functions import get_object_or_None
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.db.models import Q
from django.http.response import HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotFound
from django.utils.encoding import force_str
from django.utils.html import unquote
from haystack.backends import SQ
from haystack.inputs import AutoQuery
from haystack.query import SearchQuerySet
from rest_framework.response import Response
from rest_framework.views import APIView

from cosinnus.conf import settings
from cosinnus.forms.search import filter_searchqueryset_for_portal, filter_searchqueryset_for_read_access
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.map import (
    EXCHANGE_SEARCH_MODEL_NAMES,
    SEARCH_MODEL_NAMES,
    SEARCH_MODEL_NAMES_REVERSE,
    SEARCH_MODEL_TYPES_ALWAYS_READ_PERMISSIONS,
    SEARCH_RESULT_DETAIL_TYPE_MAP,
    CloudfileMapCard,
    HaystackMapResult,
    build_date_time,
    filter_event_or_conference_happening_during,
    filter_event_searchqueryset_by_upcoming,
)
from cosinnus.models.profile import get_user_profile_model
from cosinnus.utils.functions import ensure_list_of_ints, is_number
from cosinnus.utils.group import get_cosinnus_group_model, get_default_user_group_slugs
from cosinnus.utils.permissions import check_object_read_access

try:
    from cosinnus_event.models import Event  # noqa
except Exception:
    Event = None

USER_MODEL = get_user_model()
logger = logging.getLogger('cosinnus')

SERVER_SIDE_SEARCH_LIMIT = 200


def _better_json_loads(s):
    """Can pass pure string values and None through without exception"""
    if s is None:
        return None
    try:
        return json.loads(s)
    except ValueError:
        if isinstance(s, six.string_types):
            return s
        else:
            raise


# supported map search query parameters, and their default values (as python data after a json.loads()!) if not present
MAP_NON_CONTENT_TYPE_SEARCH_PARAMETERS = {
    'q': '',  # search query, wildcard if empty
    'sw_lat': -90,  # SW latitude, max southwest
    'sw_lon': -180,  # SW longitude, max southwest
    'ne_lat': 90,  # NE latitude, max northeast
    'ne_lon': 180,  # NE latitude, max northeast
    'limit': 20,  # result count limit, integer or None
    'page': 0,
    'topics': None,
    'text_topics': None,
    'item': None,
    'ignore_location': False,  # if True, we completely ignore locs, and even return results without location
    'mine': False,  # if True, we only show items of the current user. ignored if user not authenticated
    'external': bool(settings.COSINNUS_EXCHANGE_ENABLED),
    'fromDate': None,
    'fromTime': None,
    'toDate': None,
    'toTime': None,
    'exchange': False,
    'matching': '',
}
# supported map search query parameters for selecting content models, and their default values (as python data after a
# json.loads()!) if not present
MAP_CONTENT_TYPE_SEARCH_PARAMETERS = {
    'people': True,
    'events': True,
    'projects': True,
    'groups': True,
}

if settings.COSINNUS_MANAGED_TAGS_ENABLED:
    MAP_CONTENT_TYPE_SEARCH_PARAMETERS.update(
        {
            'managed_tags': None,
        }
    )
if settings.COSINNUS_ENABLE_SDGS:
    MAP_CONTENT_TYPE_SEARCH_PARAMETERS.update(
        {
            'sdgs': None,
        }
    )
if settings.COSINNUS_IDEAS_ENABLED:
    MAP_CONTENT_TYPE_SEARCH_PARAMETERS.update(
        {
            'ideas': True,
        }
    )
if settings.COSINNUS_ORGANIZATIONS_ENABLED:
    MAP_CONTENT_TYPE_SEARCH_PARAMETERS.update(
        {
            'organizations': True,
        }
    )
if settings.COSINNUS_CONFERENCES_ENABLED:
    MAP_CONTENT_TYPE_SEARCH_PARAMETERS.update(
        {
            'conferences': True,
        }
    )
if settings.COSINNUS_CLOUD_ENABLED:
    MAP_CONTENT_TYPE_SEARCH_PARAMETERS.update(
        {
            'cloudfiles': True,
        }
    )
if settings.COSINNUS_EXCHANGE_EXTERNAL_RESOURCES_ENABLED:
    MAP_CONTENT_TYPE_SEARCH_PARAMETERS.update(
        {
            'externalresources': True,
        }
    )

# supported map search query parameters, and their default values (as python data after a json.loads()!) if not present
MAP_SEARCH_PARAMETERS = {}
MAP_SEARCH_PARAMETERS.update(MAP_NON_CONTENT_TYPE_SEARCH_PARAMETERS)
MAP_SEARCH_PARAMETERS.update(MAP_CONTENT_TYPE_SEARCH_PARAMETERS)


class SearchQuerySetMixin:
    search_parameters = MAP_SEARCH_PARAMETERS

    def dispatch(self, request, *args, **kwargs):
        self.params = self._collect_parameters(request.GET, self.search_parameters)
        self.skip_score_sorting = False
        if 'q' in self.params:
            self.params['q'] = force_str(self.params['q'])
        # An argument can be passed to the view when calling it internally to bypass the server side search limit.
        skip_limit_backend = kwargs.pop('skip_limit_backend', False)
        if 'limit' in self.params:
            if not is_number(self.params['limit']) or self.params['limit'] < 0:
                return HttpResponseBadRequest('``limit`` param must be a positive number or 0!')
            if not skip_limit_backend:
                self.params['limit'] = min(self.params['limit'], SERVER_SIDE_SEARCH_LIMIT)
        if 'page' in self.params:
            if not is_number(self.params['page']) or self.params['page'] < 0:
                return HttpResponseBadRequest('``page`` param must be a positive number or 0!')
        return super().dispatch(request, *args, **kwargs)

    def _collect_parameters(self, param_dict, parameter_list):
        """For a GET/POST dict, collects all attributes listes as keys in ``parameter_list``.
        If not present in the GET/POST dict, the value of the key in ``parameter_list`` will be used."""
        results = {}
        for key, value in list(parameter_list.items()):
            if key in param_dict:
                results[key] = _better_json_loads(param_dict.get(key, None))
            else:
                results[key] = value
        return results

    def get_queryset(self, filter_group_id=None):
        """Search using haystack search results.

        @params: collected query params, see ``MAP_SEARCH_PARAMETERS``
        @param user: User object
        @param filter_group_id: Will filter all items by group relation, where applicable
                (i.e. users are filtered by group memberships for that group, events as events in that group)
        @param extra_filter: Optional function to apply further query filtering
        """
        user = self.request.user
        query = self.params['q']
        implicit_ignore_location = not any(
            [loc_param in self.params for loc_param in ['sw_lon', 'sw_lat', 'ne_lon', 'ne_lat']]
        )

        if not settings.COSINNUS_EXCHANGE_ENABLED:
            self.params['exchange'] = False
        if not settings.COSINNUS_MATCHING_ENABLED:
            self.params['matching'] = False

        prefer_own_portal = getattr(settings, 'MAP_API_HACKS_PREFER_OWN_PORTAL', False)

        # filter for requested model types
        model_list = [
            klass for klass, param_name in list(SEARCH_MODEL_NAMES.items()) if self.params.get(param_name, False)
        ]
        if settings.COSINNUS_EXCHANGE_ENABLED:
            model_list += [
                klass
                for klass, param_name in list(EXCHANGE_SEARCH_MODEL_NAMES.items())
                if self.params.get(param_name, False)
            ]

        sqs = SearchQuerySet().models(*model_list)

        # filter for map bounds (Points are constructed ith (lon, lat)!!!)
        if not self.params['ignore_location'] and not implicit_ignore_location:
            sqs = sqs.within(
                'location',
                Point(self.params['sw_lon'], self.params['sw_lat']),
                Point(self.params['ne_lon'], self.params['ne_lat']),
            )
        # filter for user's own content
        if self.params['mine'] and user.is_authenticated:
            user_id = user.id
            sqs = sqs.filter_and(Q(creator=user_id) | Q(user_id=user_id) | Q(group_members=user_id))
        # filter for search terms
        if query:
            # specifically include the boosted field into the autoquery so that results
            # matching a query word in the boost field get assigned a higher result.score
            sqs = sqs.filter(SQ(boosted=AutoQuery(query)) | SQ(text=AutoQuery(query)))

        # group-filtered-map view for on-group pages
        if filter_group_id:
            group = get_object_or_None(get_cosinnus_group_model(), id=filter_group_id)
            if group:
                filtered_groups = [filter_group_id]
                # get child projects of this group
                filtered_groups += [subproject.id for subproject in group.get_children() if subproject.is_active]
                sqs = sqs.filter_and(Q(membership_groups__in=filtered_groups) | Q(group__in=filtered_groups))

        # filter topics
        topics = ensure_list_of_ints(self.params.get('topics', ''))
        if topics:
            sqs = sqs.filter_and(mt_topics__in=topics)

        text_topics = ensure_list_of_ints(self.params.get('text_topics', ''))
        if text_topics:
            sqs = sqs.filter_and(mt_text_topics__in=text_topics)

        if settings.COSINNUS_ENABLE_SDGS:
            sdgs = ensure_list_of_ints(self.params.get('sdgs', ''))
            if sdgs:
                sqs = sqs.filter_and(sdgs__in=sdgs)
        if settings.COSINNUS_MANAGED_TAGS_ENABLED:
            managed_tags = ensure_list_of_ints(self.params.get('managed_tags', ''))
            if managed_tags:
                sqs = sqs.filter_and(managed_tags__in=managed_tags)
        # filter for portal visibility
        sqs = filter_searchqueryset_for_portal(
            sqs, restrict_multiportals_to_current=prefer_own_portal, exchange=self.params.get('exchange', False)
        )
        # filter for read access by this user
        sqs = filter_searchqueryset_for_read_access(sqs, user)

        params_keys = [key for key, value in self.params.items() if value]
        settings_keys = MAP_CONTENT_TYPE_SEARCH_PARAMETERS.keys()

        # filtering for events and conferences
        check_date_cts = ['events', 'conferences']
        if any([self.params.get(checktype, None) for checktype in check_date_cts]):
            sqs = sqs.exclude(is_hidden_group_proxy=True)

            # figure out if a datetime filter is active
            content_type_params = list(set(params_keys) & set(settings_keys))
            reduced_pramas = list(set(content_type_params) & set(check_date_cts))
            check_date_by_date_param = self.params.get('fromDate') or self.params.get('toDate')
            check_date_by_conten_type = len(content_type_params) == len(reduced_pramas)
            if check_date_by_date_param and check_date_by_conten_type:
                # filter by datetime range
                from_date_string = self.params.get('fromDate')
                from_time_string = self.params.get('fromTime')
                from_datetime = build_date_time(from_date_string, from_time_string)
                to_date_string = self.params.get('toDate')
                to_time_string = self.params.get('toTime')
                to_datetime = build_date_time(to_date_string, to_time_string)
                if from_datetime and to_datetime:
                    sqs = filter_event_or_conference_happening_during(from_datetime, to_datetime, sqs)
            else:
                # filter events by upcoming status and exclude hidden proxies
                sqs = filter_event_searchqueryset_by_upcoming(sqs)

        # filter all default user groups if the new dashboard is being used (they count as "on plattform" and aren't
        # shown)
        if getattr(settings, 'COSINNUS_USE_V2_DASHBOARD', False):
            sqs = sqs.exclude(is_group_model='true', slug__in=get_default_user_group_slugs())

        prefer_own_portal = getattr(settings, 'MAP_API_HACKS_PREFER_OWN_PORTAL', False)
        # if we have no query-boosted results, use *only* our custom sorting (haystack's is very random)
        if not query:
            # order groups, projects and conferences alphabetically
            if (
                any(
                    [
                        self.params.get(checktype, None)
                        for checktype in settings.COSINNUS_ALPHABETICAL_ORDER_FOR_SEARCH_MODELS_WHEN_SINGLE
                    ]
                )
                and len(model_list) == 1
            ):
                # sort by slug instead of title because haystack doesn't support
                # case-insensitive ordering
                sort_args = ['sort_field', 'title']
                self.skip_score_sorting = True
            else:
                sort_args = ['-local_boost']
            # if we only look at conferences, order them by their from_date, future first!
            if prefer_own_portal:
                sort_args = ['-portal'] + sort_args
            sqs = sqs.order_by(*sort_args)

            """
            # this would be the way to force-sort a content type by a natural ordering instead of score if its the only type being shown
            if params.get('conferences', False) and sum([1 if params.get(content_key, False) else 0 for content_key in MAP_CONTENT_TYPE_SEARCH_PARAMETERS.keys()]) == 1:
                sort_args = ['-from_date'] + sort_args
                skip_score_sorting = True
            """  # noqa

        return sqs

    def search(self, sqs):
        query = force_str(self.params['q'])
        limit = self.params['limit']
        page = self.params['page']
        item_id = self.params['item']

        prefer_own_portal = getattr(settings, 'MAP_API_HACKS_PREFER_OWN_PORTAL', False)
        # sort results into one list per model
        total_count = len(sqs)
        sqs = sqs[limit * page : limit * (page + 1)]
        results = []
        for i, result in enumerate(sqs):
            if self.skip_score_sorting:
                # if we skip score sorting and only rely on the natural ordering, we make up fake high scores
                result.score = 100000 - (limit * page) - i

            elif not query:
                # if we hae no query-boosted results, use *only* our custom sorting (haystack's is very random)
                result.score = result.local_boost
                if (
                    prefer_own_portal
                    and is_number(result.portal)
                    and int(result.portal) == CosinnusPortal.get_current().id
                ):
                    result.score += 100.0
            results.append(HaystackMapResult(result, user=self.request.user))

        # if the requested item (direct select) is not in the queryset snippet
        # (might happen because of an old URL), then mix it in as first item and drop the last
        if item_id:
            item_id = str(item_id)
            if not any([res['id'] == item_id for res in results]):
                item_result = get_searchresult_by_itemid(item_id, self.request.user)
                if item_result:
                    results = [HaystackMapResult(item_result, user=self.request.user)] + results[:-1]

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
        return {'results': results, 'page': page_obj}


class MapSearchView(SearchQuerySetMixin, APIView):
    """Maps API search endpoint using haystack search results. For parameters see ``MAP_SEARCH_PARAMETERS``
    returns JSON with the contents of type ``HaystackMapResult``

    @param filter_group_id: Will filter all items by group relation, where applicable
            (i.e. users are filtered by group memberships for that group, events as events in that group)
    """

    search_parameters = MAP_SEARCH_PARAMETERS

    def get(self, request, filter_group_id=None):
        if self.params.get('cloudfiles', False):
            return MapCloudfilesView.as_view()(request._request)

        if settings.COSINNUS_MATCHING_ENABLED and self.params.get('matching', False):
            return MapMatchingView.as_view()(request._request)

        sqs = self.get_queryset(filter_group_id=filter_group_id)
        data = self.search(sqs)
        return Response(data)


class MapMatchingView(SearchQuerySetMixin, APIView):
    """Maps API matching endpoint using haystack search results. For parameters see ``MAP_SEARCH_PARAMETERS``.
    Returns JSON with the contents of type ``HaystackMapResult`` for all projects/groups/organizations, which are
    open for cooperation (is_open_for_cooperation). Sorting is based upon matching fields with object specified by
    parameter ``matching`` and settings COSINNUS_MATCHING_FIELDS/COSINNUS_MATCHING_DYNAMIC_FIELDS

    @param filter_group_id: Will filter all items by group relation, where applicable
            (i.e. users are filtered by group memberships for that group, events as events in that group)
    """

    def get(self, request, filter_group_id=None):
        matching_result = self.get_matching_result()
        if matching_result:
            sqs = list(self.get_queryset_matching(matching_result, filter_group_id=filter_group_id))
            sqs += list(self.get_queryset_not_matching(matching_result, filter_group_id=filter_group_id))
            data = self.search(sqs)
            return Response(data)
        return Response({'results': [], 'page': None})

    def get_matching_result(self):
        """Return result described with matching parameter (e. g. project.<slug>)"""
        # get matching candidate for comparison (e. g. project.<slug>)
        matching = re.match(r'(projects|groups|organizations)\.([a-z0-9-_]+)', str(self.params.get('matching', '')))
        if not matching:
            return None
        matching_type, matching_slug = matching.groups()
        # get matching candidate
        portal = CosinnusPortal.get_current().id
        return get_searchresult_by_args(portal, matching_type, matching_slug)

    def get_filter_conditions(self, matching_result):
        # filter by fields
        conditions = Q()
        for field_name in getattr(settings, 'COSINNUS_MATCHING_FIELDS', []):
            values = matching_result.get(field_name)
            values = values if isinstance(values, (list, tuple)) else [values]
            for value in values:
                conditions |= Q(**{field_name: value})
        # filter by dynamic fields
        dynamic_fields = matching_result.dynamic_fields
        for field_name in getattr(settings, 'COSINNUS_MATCHING_DYNAMIC_FIELDS', []):
            values = dynamic_fields[field_name]
            values = values if isinstance(values, (list, tuple)) else [values]
            for value in values:
                conditions |= Q(**{f'dynamic_fields.{field_name}': value})
        return conditions

    def get_queryset_base(self, matching_result, filter_group_id=None):
        """Filter open projects, groups and organizations, excluding matching candidate itself"""
        sqs = super().get_queryset(filter_group_id=filter_group_id)
        # filter content types: project, group or organization
        sqs = sqs.filter(
            django_ct__in=(
                'cosinnus.cosinnusproject',
                'cosinnus.cosinnussociety',
                'cosinnus_organization.cosinnusorganization',
            )
        )
        # filter only candidates which are open for cooperation
        sqs = sqs.filter(is_open_for_cooperation='true')
        # exclude matching candidate itself
        sqs = sqs.exclude(_id=matching_result.id)
        return sqs

    def get_queryset_matching(self, matching_result, filter_group_id=None):
        """Filter for matching query"""
        sqs = self.get_queryset_base(matching_result, filter_group_id=filter_group_id)
        sqs = sqs.filter(self.get_filter_conditions(matching_result))
        return sqs

    def get_queryset_not_matching(self, matching_result, filter_group_id=None):
        """Filter for everything but matching query"""
        sqs = self.get_queryset_base(matching_result, filter_group_id=filter_group_id)
        sqs = sqs.exclude(self.get_filter_conditions(matching_result))
        return sqs


class MapCloudfilesView(SearchQuerySetMixin, APIView):
    def get(self, request):
        from cosinnus_cloud.hooks import get_nc_user_id
        from cosinnus_cloud.utils.nextcloud import perform_fulltext_search

        query = force_str(self.params['q'])
        limit = self.params['limit']
        page = self.params['page']

        if self.params.get('cloudfiles', False):
            return MapCloudfilesView.as_view()(request)

        result = perform_fulltext_search(get_nc_user_id(request.user), query, page=page + 1, page_size=limit)

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

        data = {'results': [CloudfileMapCard(doc, query) for doc in result['documents']], 'page': page_obj}
        return Response(data)


MAP_DETAIL_PARAMETERS = {
    'portal': -1,  # portal id, < 0 means current
    'slug': '',  # object slug
    'type': '',  # item type, as defined in `SEARCH_MODEL_NAMES`
}


class MapDetailView(SearchQuerySetMixin, APIView):
    """Maps API object detail endpoint using pSQL results. For parameters see ``MAP_DETAIL_PARAMETERS``
    returns JSON with the contents of type ``DetailedMapResult``
    """

    search_parameters = MAP_DETAIL_PARAMETERS

    def get(self, request):
        portal = self.params['portal']
        slug = self.params['slug']
        model_type = self.params['type']

        if not is_number(portal) or portal < 0:
            return HttpResponseBadRequest('``portal`` param must be a positive number!')
        if not slug:
            return HttpResponseBadRequest('``slug`` param must be supplied!')
        slug = force_str(slug)  # stringify is necessary for number-only slugs
        if not model_type or not isinstance(model_type, six.string_types):
            return HttpResponseBadRequest('``type`` param must be supplied and be a string!')

        if portal == 0:
            portal = CosinnusPortal.get_current().id

        # for internal DB based objects:
        if portal != settings.COSINNUS_EXCHANGE_PORTAL_ID:
            # try to retrieve the requested object
            model = SEARCH_MODEL_NAMES_REVERSE.get(model_type, None)
            if model is None:
                return HttpResponseBadRequest('``type`` param indicated an invalid data model type!')

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
                return HttpResponseNotFound('No item found that matches the requested type and slug (obj).')

            # check read permission
            if model_type not in SEARCH_MODEL_TYPES_ALWAYS_READ_PERMISSIONS and not check_object_read_access(
                obj, request.user
            ):
                return HttpResponseForbidden('You do not have permission to access this item.')
            # get the basic result data from the search index (as it is already prepared and faster to access there)
            haystack_result = get_searchresult_by_args(portal, model_type, slug)
            if not haystack_result:
                return HttpResponseNotFound('No item found that matches the requested type and slug (index).')
            # format data
            result_model = SEARCH_RESULT_DETAIL_TYPE_MAP[model_type]
            result = result_model(haystack_result, obj, request.user, request=request)
        else:
            # for external, api based objects:
            haystack_result = get_searchresult_by_args(portal, model_type, slug)
            if not haystack_result:
                return HttpResponseNotFound('No item found that matches the requested type and slug (external).')
            result = HaystackMapResult(haystack_result, request.user, request=request)

        data = {
            'result': result,
        }
        return Response(data)


def get_searchresult_by_itemid(itemid, user=None):
    portal, model_type, slug = itemid.split('.', 2)
    return get_searchresult_by_args(portal, model_type, slug, user=user)


def get_searchresult_by_args(portal, model_type, slug, user=None):
    """Retrieves a HaystackMapResult just as the API would, for a given shortid
    in the form of `<classid>.<instanceid>` (see `itemid_from_searchresult()`)."""

    # convert url parameters to indexed values
    try:
        portal = int(portal)
    except Exception:
        pass
    slug = unquote(slug)

    # if the portal id is COSINNUS_EXCHANGE_PORTAL_ID, we have an external item, so look up the external models
    if settings.COSINNUS_EXCHANGE_ENABLED and portal == settings.COSINNUS_EXCHANGE_PORTAL_ID:
        from cosinnus.models.map import EXCHANGE_SEARCH_MODEL_NAMES_REVERSE

        model = EXCHANGE_SEARCH_MODEL_NAMES_REVERSE.get(model_type, None)
    else:
        model = SEARCH_MODEL_NAMES_REVERSE.get(model_type, None)

    if model_type == 'people':
        sqs = SearchQuerySet().models(model).filter_and(slug=slug)
    elif model_type == 'events' and '*' in slug:
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
        logger.warn(
            'Got a DetailMap request where %d indexed results were found!' % len(sqs),
            extra={
                'portal': portal,
                'model': model,
                'slug': slug,
            },
        )
        return None
    return sqs[0]


map_search_endpoint = MapSearchView.as_view()
map_matching_endpoint = MapMatchingView.as_view()
map_detail_endpoint = MapDetailView.as_view()
