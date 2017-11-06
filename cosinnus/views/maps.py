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
from cosinnus.templatetags.cosinnus_tags import full_name_force,\
    render_cosinnus_topics_field
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
from django.forms.forms import BaseForm
from django.utils.html import escape


USER_MODEL = get_user_model()


class MapView(TemplateView):

    def get_context_data(self, **kwargs):
        # Instantiate map state
        # TODO: sadly, these are ignored, as the JS takes the client's default settings on router /map/ auto init
        
        """
        Unused for now, could be defined, but would then also have to be passsed in the template,
        in a similar way to passing the arguments in group_list.html.
        settings = {
            'availableFilters': {
                 'people': True,
                 'events': True,
                 'projects': True,
                 'groups': True
            },
            'activeFilters': {
                'people': True,
                'events': True,
                'projects': True,
                'groups': True
            },
            'markerIcons': get_map_marker_icon_settings(),
        }
        """
        return {
            'markers': get_map_marker_icon_settings_json(),
        }

    template_name = 'cosinnus/map/map_page.html'

map_view = MapView.as_view()


class MapEmbedView(TemplateView):
    """ An embeddable, resizable Map view without any other elements than the map """
    
    template_name = 'cosinnus/universal/map/map_embed.html'
    
    @method_decorator(xframe_options_exempt)
    def dispatch(self, *args, **kwargs):
        return super(MapEmbedView, self).dispatch(*args, **kwargs)

map_embed_view = MapEmbedView.as_view()





""" 
    DEPRECATION:

    Everything below this point is deprecated and can be should now longer be used. 
    It is kept only for legacy search purposes until all portals have switched to haystack search.
"""


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


def _filter_qs_topics(qs, params, media_tag_object_prefix='media_tag__'):
    """ Filters a Queryset for latitude, longitude inside a given bounding box.
        @return: the filtered Queryset """
    topic_ids = ensure_list_of_ints(params.get('topics', ''))
    if not topic_ids:
        return qs
    media_tag_object_prefix = media_tag_object_prefix + 'topics'
    
    def filter_topic(qs, topic_id):
        return qs.filter( Q(**{media_tag_object_prefix+'__startswith':topic_id+','}) | Q(**{media_tag_object_prefix+'__endswith':','+topic_id}) | Q(**{media_tag_object_prefix+'__contains':',%s,' % topic_id}) | Q(**{media_tag_object_prefix+'__exact':topic_id}) )
    
    for topic in topic_ids:
        qs = filter_topic(qs, str(topic))
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


def map_search_endpoint(request, filter_group_id=None):
    """ Maps API search endpoints. For parameters see ``MAP_PARAMETERS``
        returns JSON with the contents of type ``MapSearchResults``
        
        @param filter_group_id: Will filter all items by group relation, where applicable 
                (i.e. users are filtered by group memberships for that group, events as events in that group)
        """
    
    params = _collect_parameters(request.GET, MAP_PARAMETERS)
    query = force_text(params['q'])

    # return equal count parts of the data limit for each dataset
    datasets = [setname for setname in ['people', 'projects', 'groups', 'events'] if params[setname]]
    limit_per_set = 100000
    limit = params['limit']
    if limit and datasets:
        if not is_number(limit) or limit < 0:
            return HttpResponseBadRequest('``limit`` param must be a positive number or 0!')
        limit_per_set = int(float(limit) / float(len(datasets))) if limit != 0 else limit_per_set
        if limit > 0 and limit_per_set < 1:
            limit_per_set = 1

    results = {}
    if params['people']:
        people = []
        user_qs = _get_user_base_queryset(request)
        user_qs = _filter_qs_location_bounds(user_qs, params, 'cosinnus_profile__media_tag__')
        user_qs = _filter_qs_topics(user_qs, params, 'cosinnus_profile__media_tag__')
        if query:
            user_qs = _filter_qs_text(user_qs, query, ['first_name', 'last_name'])
        # filter for group members of optinally given group id
        if filter_group_id:
            filter_group_id = int(filter_group_id)
            # id could be of a CoinnusProject or CosinnusGroup (seperate cache)
            group = CosinnusProject.objects.get_by_id(filter_group_id)
            if not group:
                group = CosinnusSociety.objects.get_by_id(filter_group_id)
            if group:
                user_qs = user_qs.filter(id__in=group.members)
            else:
                user_qs = []
        for user in user_qs[:limit_per_set]:
            people.append(UserMapResult(user))
        results['people'] = people

    if params['projects']:
        projects = []
        projects_qs = _get_projects_base_queryset(request)
        projects_qs = _filter_qs_location_bounds(projects_qs, params, 'locations__')
        projects_qs = _filter_qs_topics(projects_qs, params)
        if query:
            projects_qs = _filter_qs_text(projects_qs, query, CosinnusProject.NAME_LOOKUP_FIELDS)
        if filter_group_id:
            projects_qs = projects_qs.filter(parent_id=filter_group_id)
        for project in projects_qs[:limit_per_set]:
            projects.append(GroupMapResult(project))
        results['projects'] = projects

    if params['groups']:
        groups = []
        groups_qs = _get_societies_base_queryset(request)
        groups_qs = _filter_qs_location_bounds(groups_qs, params, 'locations__')
        groups_qs = _filter_qs_topics(groups_qs, params)
        if query:
            groups_qs = _filter_qs_text(groups_qs, query, CosinnusSociety.NAME_LOOKUP_FIELDS)
        for group in groups_qs[:limit_per_set]:
            groups.append(GroupMapResult(group))
        results['groups'] = groups

    if params['events']:
        events = []
        events_qs = _get_events_base_queryset(request)
        if events_qs:
            events_qs = _filter_qs_location_bounds(events_qs, params, 'media_tag__')
            events_qs = _filter_qs_topics(events_qs, params)
            if query:
                events_qs = _filter_qs_text(events_qs, query, ['title'])
            if filter_group_id:
                events_qs = events_qs.filter(group_id=filter_group_id)
        for event in events_qs[:limit_per_set]:
            events.append(EventMapResult(event))
        results['events'] = events

    data = MapSearchResults(**results)
    return JsonResponse(data)
