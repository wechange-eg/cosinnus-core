# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model, login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.urlresolvers import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from cosinnus.core.decorators.views import staff_required, superuser_required,\
    redirect_to_not_logged_in, redirect_to_403
from cosinnus.forms.user import UserCreationForm, UserChangeForm
from cosinnus.views.mixins.ajax import patch_body_json_data
from cosinnus.utils.http import JSONResponse
from django.contrib import messages
from cosinnus.models.profile import get_user_profile_model
from cosinnus.models.tagged import BaseTagObject
from cosinnus.models.group import CosinnusPortal
from cosinnus.core.mail import MailThread, get_common_mail_context,\
    send_mail_or_fail_threaded
from django.template.loader import render_to_string
from django.http.response import HttpResponseNotAllowed, JsonResponse,\
    HttpResponseBadRequest, HttpResponse
from django.shortcuts import redirect
from cosinnus.templatetags.cosinnus_tags import full_name_force
from django.contrib.auth.views import password_reset, password_change
from cosinnus.utils.permissions import check_user_integrated_portal_member,\
    filter_tagged_object_queryset_for_user
from django.template.context import RequestContext
from django.template.response import TemplateResponse
from django.core.paginator import Paginator
from cosinnus.views.mixins.group import EndlessPaginationMixin
import json
from cosinnus.utils.user import filter_active_users
from django.conf import settings
from cosinnus.models.group_extra import CosinnusSociety, CosinnusProject
from django.contrib.staticfiles.templatetags.staticfiles import static
from cosinnus.utils.functions import is_number, ensure_list_of_ints
import six
from django.db.models import Q
from operator import __or__ as OR, __and__ as AND
from django.utils.encoding import force_text
from cosinnus.templatetags.cosinnus_map_tags import get_map_marker_icon_settings,\
    get_map_marker_icon_settings_json
from django.views.generic.base import TemplateView
from django.views.decorators.clickjacking import xframe_options_exempt
from cosinnus.forms.search import filter_searchqueryset_for_read_access
from django.utils.timezone import now
import datetime
import collections


USER_MODEL = get_user_model()


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


def _get_user_base_queryset(request):
    all_users = filter_active_users(get_user_model().objects.filter(id__in=CosinnusPortal.get_current().members))

    if request.user.is_authenticated():
        visibility_level = BaseTagObject.VISIBILITY_GROUP
    else:
        visibility_level = BaseTagObject.VISIBILITY_ALL

    # only show users with the visibility level
    qs = all_users.filter(cosinnus_profile__media_tag__visibility__gte=visibility_level)
    return qs

def _get_societies_base_queryset(request):
    """ FIXME: Circumventing group caching here so we can get a QS """
    qs = CosinnusSociety.objects.all_in_portal()
    if not (settings.COSINNUS_SHOW_PRIVATE_GROUPS_FOR_ANONYMOUS_USERS or request.user.is_authenticated()):
        qs = qs.filter(public=True)
    return qs

def _get_projects_base_queryset(request):
    """ FIXME: Circumventing group caching here so we can get a QS """
    qs = CosinnusProject.objects.all_in_portal()
    if not (settings.COSINNUS_SHOW_PRIVATE_GROUPS_FOR_ANONYMOUS_USERS or request.user.is_authenticated()):
        qs = qs.filter(public=True)
    return qs

def _get_events_base_queryset(request, show_past_events=False):
    try:
        from cosinnus_event.models import Event, upcoming_event_filter
    except:
        return []
    qs = Event.objects.filter(group__portal=CosinnusPortal.get_current())
    qs = filter_tagged_object_queryset_for_user(qs, request.user)
    qs = qs.filter(state=Event.STATE_SCHEDULED)
    if not show_past_events:
        qs = upcoming_event_filter(qs)
    return qs



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

class UserMapResult(MapResult):
    """ Takes a ``get_user_model()`` object and funnels its properties into a proper MapResult """

    def __init__(self, user, *args, **kwargs):
        return super(UserMapResult, self).__init__(
            user.cosinnus_profile.media_tag.location_lat,
            user.cosinnus_profile.media_tag.location_lon,
            user.cosinnus_profile.media_tag.location,
            user.get_full_name(),
            user.cosinnus_profile.get_absolute_url(),
            user.cosinnus_profile.get_map_marker_image_url(),
            user.cosinnus_profile.description,
        )

class GroupMapResult(MapResult):
    """ Takes a ``get_user_model()`` object and funnels its properties into a proper MapResult

        Note: Only returns 1 Map Result for each group, even if the group has multiple Locations set.
              Returns the first location set on the group.
    """

    def __init__(self, group, *args, **kwargs):
        # only return one resu
        loc = group.locations.all()[0]
        return super(GroupMapResult, self).__init__(
            loc.location_lat,
            loc.location_lon,
            loc.location,
            group['name'],
            group.get_absolute_url(),
            group.get_map_marker_image_url() or static('images/group-avatar-placeholder.png'),
            group['description_long'] or group['description'],
        )

class EventMapResult(MapResult):
    """ Takes a ``get_user_model()`` object and funnels its properties into a proper MapResult """

    def __init__(self, event, *args, **kwargs):
        return super(EventMapResult, self).__init__(
            event.media_tag.location_lat,
            event.media_tag.location_lon,
            event.media_tag.location,
            event.title,
            event.get_absolute_url(),
            (event.attached_image and event.attached_image.static_image_url()) or static('images/event-image-placeholder.png'),
            event.note,
        )


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
    'limit': None, # result count limit, integer or None
    'topics': None,
}

def _filter_qs_location_bounds(qs, params, location_object_prefix='media_tag__'):
    """ Filters a Queryset for latitude, longitude inside a given bounding box.
        @return: the filtered Queryset """
    filter_kwargs = {
        location_object_prefix + 'location_lat__gte': params['sw_lat'],
        location_object_prefix + 'location_lon__gte':params['sw_lon'],
        location_object_prefix + 'location_lat__lte':params['ne_lat'],
        location_object_prefix + 'location_lon__lte':params['ne_lon'],
    }
    qs = qs.exclude(**{location_object_prefix + 'location_lat': None})
    qs = qs.filter(**filter_kwargs)
    return qs


def _filter_qs_text(qs, text, attributes=['title',]):
    """ Filters a Queryset for a text string.
        The text string will be whitespace-tokenized and QS will be filtered for __icontains,
        ANDed by-token, and ORed by object attribute, so that each token must appear in at least on of the attributes
        @return: the filtered Queryset """
    and_tokens = []
    for token in text.split():
        or_attrs = []
        for attr in attributes:
            or_attrs.append(Q(**{attr + '__icontains': token}))
        and_tokens.append(reduce(OR, or_attrs))
    qs = qs.filter(reduce(AND, and_tokens))
    return qs


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

def map_search_endpoint(request, filter_group_id=None):
    """ Maps API search endpoints. For parameters see ``MAP_PARAMETERS``
        returns JSON with the contents of type ``MapSearchResults``
        
        @param filter_group_id: Will filter all items by group relation, where applicable 
                (i.e. users are filtered by group memberships for that group, events as events in that group)
        """
    
    
    
    """ TODO: filter locations like this: """
    
    from haystack.utils.geo import Point
    from haystack.query import SearchQuerySet
    
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
    print ">> topis?", params.get('topics', '')
    print ">> got", request.GET
    if topics: 
        print ">> filtering for topics:", topics
        sqs = sqs.filter_and(mt_topics__in=topics)
    # filter for read access by this user
    sqs = filter_searchqueryset_for_read_access(sqs, request.user)
    # filter events by upcoming status
    if params['events'] and Event is not None:
        _now = now()
        event_horizon = datetime.datetime(_now.year, _now.month, _now.day)
        sqs = sqs.exclude(Q(to_date__lt=event_horizon) | (Q(_missing_='to_date') & Q(from_date__lt=event_horizon)))
        pass 
        
    """ CHECK: user visibility like in profile settings """
        
    for res in sqs:
        print ">> res:", res.boosted[:14], res.model, res.app_label, res.model_name, res.from_date, res.needs_date_filtering
    
    
    sqs = sqs[:limit]
    
    # sort results into one list per model
    results = collections.defaultdict(list)
    for result in sqs:
        print ">> adding results for", result.model, result
        results[SEARCH_MODEL_NAMES[result.model]].append(HaystackMapResult(result))
    
    data = MapSearchResults(**results)
    return JsonResponse(data)

    # ----------------
