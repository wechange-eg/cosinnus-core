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
from django.http.response import HttpResponseNotAllowed, JsonResponse
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


USER_MODEL = get_user_model()


class MapView(ListView):

    model = USER_MODEL

    def get_context_data(self, **kwargs):
        # Instantiate controls state.
        return {
            'filters': {
                'people': True,
                'events': True,
                'projects': True,
                'groups': True
            },
            'layer': 'street'
        }

    template_name = 'cosinnus/map/map-page.html'


map_view = MapView.as_view()



def _collect_parameters(param_dict, parameter_list):
    """ For a GET/POST dict, collects all attributes listes as keys in ``parameter_list``. 
        If not present in the GET/POST dict, the value of the key in ``parameter_list`` will be used. """
    results = {}
    for key, value in parameter_list.items():
        if key in param_dict:
            results[key] = json.loads(param_dict.get(key)) if param_dict.get(key) else None
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
        from cosinnus_events.models import Event, upcoming_event_filter
    except:
        return []
    qs = Event.objects.all()
    qs = filter_tagged_object_queryset_for_user(qs, request.user)
    qs = qs.filter(state=Event.STATE_SCHEDULED)
    if not show_past_events:
        qs = upcoming_event_filter(qs)
    return qs



class MapResult(dict):
    """ A single result for the search of the map, enforcing required fields """
    
    def __init__(self, lat, lon, address, title, url=None, imageUrl=None, *args, **kwargs):
        self['lat'] = lat
        self['lon'] = lon
        self['address'] = address
        self['title'] = title
        self['url'] = url
        self['imageUrl'] = imageUrl
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
            user.cosinnus_profile.get_avatar_thumbnail_url() or static('images/jane-doe.png') # FIXME: TOOD: compatibility with custom DRJA avatars!
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
    'sw_lon': 180, # SW longitude, max southwest
    'ne_lat': 90, # NE latitude, max northeast
    'ne_lon': -180, # NE latitude, max northeast
    'people': True,
    'events': True,
    'projects': True,
    'groups': True,
    'limit': None, # result count limit, integer or None
}

def _filter_qs_location_bounds(qs, params, media_tag_prefix=''):
    """ Filters a Queryset for latitude, longitude inside a given bounding box.
        @return: the filtered Queryset """
    filter_kwargs = {
        media_tag_prefix + 'media_tag__location_lat__gte': params['sw_lat'],
        media_tag_prefix + 'media_tag__location_lon__lte':params['sw_lon'],
        media_tag_prefix + 'media_tag__location_lat__lte':params['ne_lat'],
        media_tag_prefix + 'media_tag__location_lon__gte':params['ne_lon'],
    }
    qs = qs.exclude(**{media_tag_prefix + 'media_tag__location_lat': None})
    qs = qs.filter(**filter_kwargs)
    return qs
    
    
def map_search_endpoint(request):
    """ Maps API search endpoints. For parameters see ``MAP_PARAMETERS`` 
        returns JSON with the contents of type ``MapSearchResults``"""
    
    params = _collect_parameters(request.GET, MAP_PARAMETERS)
    
    results = {}
    if params['people']:
        people = []
        user_qs = _get_user_base_queryset(request)
        user_qs = _filter_qs_location_bounds(user_qs, params, 'cosinnus_profile__')
        for user in user_qs:
            people.append(UserMapResult(user))
            
        results['people'] = people
    
    data = MapSearchResults(**results)
    return JsonResponse(data)

    


