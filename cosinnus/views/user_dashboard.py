# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import json
import six

from annoying.functions import get_object_or_None
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured, ValidationError, \
    PermissionDenied
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.views.generic import (CreateView, DeleteView, DetailView,
    ListView, UpdateView, TemplateView)

from cosinnus.conf import settings
from cosinnus.core import signals
from cosinnus.core.registries import app_registry
from cosinnus.core.registries.group_models import group_model_registry
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety, \
    ensure_group_type
from cosinnus.utils.urls import group_aware_reverse, get_non_cms_root_url
from django.views.generic.base import View
from django.http.response import JsonResponse, HttpResponseForbidden,\
    HttpResponseBadRequest
from cosinnus.views.mixins.group import RequireLoggedInMixin
from cosinnus.models.group import CosinnusGroup, CosinnusPortal
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.models.idea import CosinnusIdea
from django.contrib.contenttypes.models import ContentType
from cosinnus.models.tagged import LikeObject, BaseTaggableObjectModel,\
    BaseHierarchicalTaggableObjectModel, BaseTagObject
from cosinnus.models.map import SEARCH_MODEL_NAMES_REVERSE
import inspect
from cosinnus.utils.filters import exclude_special_folders
from cosinnus.views.mixins.reflected_objects import MixReflectedObjectsMixin
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user
from django.db.models.query_utils import Q
from django.template.defaultfilters import date as django_date_filter
from cosinnus.templatetags.cosinnus_tags import full_name

logger = logging.getLogger('cosinnus')



class DashboardItem(dict):
    
    icon = None
    text = None
    url = None
    subtext = None
    is_emphasized = False
    
    def __init__(self, obj=None, is_emphasized=False, user=None):
        if obj:
            if is_emphasized:
                self['is_emphasized'] = is_emphasized
            # smart conversion by known models
            if type(obj) is get_cosinnus_group_model() or issubclass(obj.__class__, get_cosinnus_group_model()):
                self['icon'] = 'fa-sitemap' if obj.type == CosinnusGroup.TYPE_SOCIETY else 'fa-group'
                self['text'] = obj.name
                self['url'] = obj.get_absolute_url()
            elif type(obj) is CosinnusIdea:
                self['icon'] = 'fa-lightbulb-o'
                self['text'] = obj.title
                self['url'] = obj.get_absolute_url()
            elif obj._meta.model.__name__ == 'Message':
                self['icon'] = 'fa-envelope'
                self['text'] = obj.subject
                self['url'] = reverse('postman:view_conversation', kwargs={'thread_id': obj.thread_id}) if obj.thread_id else obj.get_absolute_url()
                self['subtext'] = ', '.join([full_name(participant) for participant in obj.other_participants(user)])
            elif BaseTaggableObjectModel in inspect.getmro(obj.__class__):
                self['icon'] = 'fa-question'
                self['text'] = obj.title
                self['url'] = obj.get_absolute_url()
                self['subtext'] = obj.group.name
                if obj.__class__.__name__ == 'Event':
                    if obj.state == 2:
                        self['icon'] = 'fa-calendar-check-o'
                    else:
                        self['subtext'] = {'is_date': True, 'date': django_date_filter(obj.from_date, 'Y-m-d')}
                        self['icon'] = 'fa-calendar'
                if obj.__class__.__name__ == 'Etherpad':
                    self['icon'] = 'fa-file-text'
                if obj.__class__.__name__ == 'Ethercalc':
                    self['icon'] = 'fa-table'
                if obj.__class__.__name__ == 'FileEntry':
                    self['icon'] = 'fa-file'
                if obj.__class__.__name__ == 'Message':
                    self['icon'] = 'fa-envelope'
                if obj.__class__.__name__ == 'TodoEntry':
                    self['icon'] = 'fa-tasks'
                if obj.__class__.__name__ == 'Poll':
                    self['icon'] = 'fa-bar-chart'


class UserDashboardView(TemplateView):
    
    template_name = 'cosinnus/user_dashboard/user_dashboard.html'
    
    def get_context_data(self, **kwargs):
        options = {
            
        }
        ctx = {
            'user_dashboard_options_json': json.dumps(options),
        }
        return ctx


user_dashboard_view = UserDashboardView.as_view()


class BaseUserDashboardWidgetView(View):
    
    http_method_names = ['get',]
    
    def get(self, request, *args, **kwargs):
        # require authenticated user
        if not request.user.is_authenticated:
            return HttpResponseForbidden('Not authenticated.')
        
        response = {
            'data': self.get_data(**kwargs),
        }
        return JsonResponse(response)
    

class GroupWidgetView(BaseUserDashboardWidgetView):
    """ Shows (for now) unlimited, all projects clustered by groups of a user.
        TODO: implement sorting by last accessed
        TODO: implement limiting to 3 projects per group and n total items.
        TODO: use clever caching """
        
    
    def get_data(self, *kwargs):
        clusters = []
        projects = list(CosinnusProject.objects.get_for_user(self.request.user))
        societies = list(CosinnusSociety.objects.get_for_user(self.request.user))
        
        filter_group_slugs = getattr(settings, 'NEWW_DEFAULT_USER_GROUPS', [])
        for society in societies:
            if society.slug in filter_group_slugs:
                continue
            
            items = [DashboardItem(society, is_emphasized=True)]
            for i in range(len(projects)-1, 0, -1):
                project = projects[i]
                if project.parent == society:
                    items.append(DashboardItem(project))
                    projects.pop(i)
            clusters.append(items)
            
        # add unclustered projects as own cluster
        clusters.extend([[DashboardItem(proj)] for proj in projects])
        
        return {'group_clusters': clusters}

api_user_groups = GroupWidgetView.as_view()


class LikedIdeasWidgetView(BaseUserDashboardWidgetView):
    """ Shows all unlimited (for now) ideas the user likes. """
    
    def get_data(self, *kwargs):
        idea_ct = ContentType.objects.get_for_model(CosinnusIdea)
        likeobjects = LikeObject.objects.filter(user=self.request.user, content_type=idea_ct) 
        liked_ideas_ids = likeobjects.values_list('object_id', flat=True)
        liked_ideas = CosinnusIdea.objects.filter(id__in=liked_ideas_ids)
        ideas = [DashboardItem(idea) for idea in liked_ideas]
        return {'items': ideas}

api_user_liked_ideas = LikedIdeasWidgetView.as_view()


class TypedContentWidgetView(BaseUserDashboardWidgetView):
    """ Shows all unlimited (for now) ideas the user likes. """
    
    model = None 
    
    def get(self, request, *args, **kwargs):
        content = kwargs.pop('content', None)
        if not content:
            return HttpResponseBadRequest('No content type supplied')
        self.model = SEARCH_MODEL_NAMES_REVERSE.get(content, None)
        if not self.model:
            return HttpResponseBadRequest('Unknown content type supplied: "%s"' % content)
        
        return super(TypedContentWidgetView, self).get(request, *args, **kwargs)
    
    def get_data(self, **kwargs):
        user = self.request.user
        # TODO: set by parameter for the "show only from my groups and projects"
        only_mine = True
        ct = ContentType.objects.get_for_model(self.model)
        model_name = '%s.%s' % (ct.app_label, ct.model_class().__name__)
        
        queryset = None
        skip_filters = False
        if BaseHierarchicalTaggableObjectModel in inspect.getmro(self.model):
            queryset = self.model._default_manager.filter(is_container=False)
            queryset = exclude_special_folders(queryset)
        elif model_name == 'cosinnus_event.Event':
            queryset = self.model.objects.all_upcoming()
        elif BaseTaggableObjectModel in inspect.getmro(self.model):
            queryset = self.model._default_manager.all()
        elif model_name == "postman.Message":
            queryset = self.model.objects.inbox(self.request.user)
            skip_filters = True
        else:
            return {'items':[], 'widget_title': '(error: %s)' % self.model.__name__}
    
        assert queryset is not None
        items = []
        if not skip_filters:
            # mix in reflected objects
            if model_name.lower() in settings.COSINNUS_REFLECTABLE_OBJECTS and \
                        BaseTaggableObjectModel in inspect.getmro(self.model):
                mixin = MixReflectedObjectsMixin()
                queryset = mixin.mix_queryset(queryset, self.model, None, user)
            
            # always filter for all portals in pool
            portal_list = [CosinnusPortal.get_current().id] + getattr(settings, 'COSINNUS_SEARCH_DISPLAY_FOREIGN_PORTALS', [])
            queryset = queryset.filter(group__portal__id__in=portal_list)
            
            user_group_ids = get_cosinnus_group_model().objects.get_for_user_pks(user)
            filter_q = Q(group__pk__in=user_group_ids)
            # if the switch is on, also include public posts from all portals
            if not only_mine:
                filter_q = filter_q | Q(media_tag__visibility=BaseTagObject.VISIBILITY_ALL)
            queryset = queryset.filter(filter_q)

            
            # filter for read permissions for user
            queryset = filter_tagged_object_queryset_for_user(queryset, user)
            
            # TODO "last-visited" ordering!
            queryset = queryset.order_by('-created')
            
        # TODO real limiting
        queryset = queryset[:5]
        
        items = [DashboardItem(item, user=self.request.user) for item in queryset]
            
        return {
            'items': items,
            'widget_title': self.model._meta.verbose_name_plural,
        }

api_user_typed_content = TypedContentWidgetView.as_view()





