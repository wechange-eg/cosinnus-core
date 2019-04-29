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
from django.http.response import JsonResponse, HttpResponseForbidden
from cosinnus.views.mixins.group import RequireLoggedInMixin
from cosinnus.models.group import CosinnusGroup
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.models.idea import CosinnusIdea
from django.contrib.contenttypes.models import ContentType
from cosinnus.models.tagged import LikeObject


logger = logging.getLogger('cosinnus')



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

class DashboardItem(dict):
    
    icon = None
    text = None
    url = None
    subtext = None
    
    def __init__(self, obj=None):
        if obj:
            # smart conversion by known models
            if type(obj) is get_cosinnus_group_model() or issubclass(obj.__class__, get_cosinnus_group_model()):
                self['icon'] = 'fa-sitemap' if obj.type == CosinnusGroup.TYPE_SOCIETY else 'fa-group'
                self['text'] = obj.name
                self['url'] = obj.get_absolute_url()
            elif type(obj) is CosinnusIdea:
                self['icon'] = 'fa-lightbulb-o'
                self['text'] = obj.title
                self['url'] = obj.get_absolute_url()
    
    

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
            
            items = [DashboardItem(society)]
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



