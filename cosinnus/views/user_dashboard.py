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
    HttpResponseBadRequest, HttpResponse
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
from cosinnus.models.user_dashboard import DashboardItem
import itertools
from numpy import sort

logger = logging.getLogger('cosinnus')


class UserDashboardView(TemplateView):
    
    template_name = 'cosinnus/user_dashboard/user_dashboard.html'
    
    def get_context_data(self, **kwargs):
        forum_group = None
        forum_slug = getattr(settings, 'NEWW_FORUM_GROUP_SLUG', None)
        if forum_slug:
            forum_group = get_object_or_None(get_cosinnus_group_model(), slug=forum_slug, portal=CosinnusPortal.get_current())
            note_form = None
            try:
                from cosinnus_note.forms import NoteForm
                note_form = NoteForm(group=forum_group)
            except: 
                if settings.DEBUG:
                    raise
            
        options = {
            
        }
        ctx = {
            'user_dashboard_options_json': json.dumps(options),
            'forum_group': forum_group,
            'note_form' : note_form,
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


class ModelRetrievalMixin(object):
    """ Mixin for all dashboard views requiring content data """
    
    def fetch_queryset_for_user(self, model, user, sort_key=None, only_mine=True):
        """ Retrieves a queryset of sorted content items for a user, for a given model.
            @param model: An actual model. Supported are all `BaseTaggableObjectModel`s,
                `CosinnusIdea`, and `postman.Message`
            @param user: Querysets are filtered by view permission for this user
            @param sort_key: (optional) the key for the `order_by` clause for the queryset
            @param only_mine: if True, will only show objects that belong to groups or projects
                the `user` is a member of. 
                If False, will include all visible items in this portal for the user. 
        """
        
        ct = ContentType.objects.get_for_model(model)
        model_name = '%s.%s' % (ct.app_label, ct.model_class().__name__)
        
        queryset = None
        skip_filters = False
        if BaseHierarchicalTaggableObjectModel in inspect.getmro(model):
            queryset = model._default_manager.filter(is_container=False)
            queryset = exclude_special_folders(queryset)
        elif model_name == 'cosinnus_event.Event':
            queryset = model.objects.all_upcoming()
        elif model is CosinnusIdea or BaseTaggableObjectModel in inspect.getmro(model):
            queryset = model._default_manager.all()
        elif model_name == "postman.Message":
            queryset = model.objects.inbox(user)
            skip_filters = True
        else:
            return None
    
        assert queryset is not None
        if not skip_filters:
            # mix in reflected objects
            if model_name.lower() in settings.COSINNUS_REFLECTABLE_OBJECTS and \
                        BaseTaggableObjectModel in inspect.getmro(model):
                mixin = MixReflectedObjectsMixin()
                queryset = mixin.mix_queryset(queryset, model, None, user)
            
            # always filter for all portals in pool
            portal_list = [CosinnusPortal.get_current().id] + getattr(settings, 'COSINNUS_SEARCH_DISPLAY_FOREIGN_PORTALS', [])
            if model is CosinnusIdea:
                queryset = queryset.filter(portal__id__in=portal_list)
            else:
                queryset = queryset.filter(group__portal__id__in=portal_list)
                user_group_ids = get_cosinnus_group_model().objects.get_for_user_pks(user)
                filter_q = Q(group__pk__in=user_group_ids)
                # if the switch is on, also include public posts from all portals
                if not only_mine:
                    filter_q = filter_q | Q(media_tag__visibility=BaseTagObject.VISIBILITY_ALL)
                queryset = queryset.filter(filter_q)
    
                # filter for read permissions for user
                queryset = filter_tagged_object_queryset_for_user(queryset, user)
            
            if sort_key:
                queryset = queryset.order_by('-created')
        return queryset
    

class TypedContentWidgetView(ModelRetrievalMixin, BaseUserDashboardWidgetView):
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
        # TODO: set by parameter for the "show only from my groups and projects"
        only_mine = True
        # TODO "last-visited" ordering!
        sort_key = '-created' 
        
        queryset = self.fetch_queryset_for_user(self.model, self.request.user, sort_key=sort_key, only_mine=only_mine)
        if queryset is None:
            return {'items':[], 'widget_title': '(error: %s)' % self.model.__name__}
        
        # TODO real limiting
        queryset = queryset[:3]
        
        items = [DashboardItem(item, user=self.request.user) for item in queryset]
            
        return {
            'items': items,
            'widget_title': self.model._meta.verbose_name_plural,
        }

api_user_typed_content = TypedContentWidgetView.as_view()



class TimelineView(ModelRetrievalMixin, View):
    """ Timeline view for a user.
        Returns items as rendered HTML. 
        Accepts content type filters and pagination parameters. """
    
    http_method_names = ['get',]
    
    # which models can be displaed, as found in `SEARCH_MODEL_NAMES_REVERSE`
    content_types = ['polls', 'todos', 'files', 'pads', 'ideas', 'events', 'notes',]
    # the key by which the timeline stream is ordered. must be present on *all* models
    sort_key = '-created' # TODO: add "last_activity" to BaseTaggableModel!
    # how many items from a queryset can be retrieved for a single stream
    
    page_size = None
    default_page_size = 5
    max_page_size = 20
    
    offset = None
    default_offset = 0
    max_offset = 100
    
    only_mine = None
    only_mine_default = False
    
    filter_model = None # if set, only show items of this model
    user = None # set at initialization
    
    
    def get(self, request, *args, **kwargs):
        # require authenticated user
        self.user = request.user
        if not request.user.is_authenticated:
            return HttpResponseForbidden('Not authenticated.')
        content = kwargs.pop('content', None)
        if content:
            self.filter_model = SEARCH_MODEL_NAMES_REVERSE.get(content, None)
            if not self.filter_model:
                return HttpResponseBadRequest('Unknown content type supplied: "%s"' % content)
        
        self.page_size = min(request.GET.get('page_size', self.default_page_size), self.max_page_size)
        self.offset = min(request.GET.get('offset', self.default_offset), self.max_offset)
        self.only_mine = request.GET.get('only_mine', self.only_mine_default)
        
        items = self.get_items()
        rendered_items = [self.render_item(item) for item in items]
        response = {
            'items': rendered_items,
            'count': len(rendered_items),
            'has_more': len(rendered_items) == self.page_size,
            'only_mine': self.only_mine,
        }
        return JsonResponse(response)
    
    def get_items(self):
        """ Returns a paginated list of items as mixture of different models, in sorted order """
        if self.filter_model:
            single_querysets = [self._get_queryset_for_model(self.filter_model)]
        else:
            single_querysets = []
            for content_type in self.content_types:
                content_model = SEARCH_MODEL_NAMES_REVERSE.get(content_type, None)
                if content_model is None:
                    if settings.DEBUG:
                        raise ImproperlyConfigured('Could not find content model for timeline content type "%s"' % content_type)
                    continue
                single_querysets.append(self._get_queryset_for_model(content_model))
                
        items = self._mix_items_from_querysets(*single_querysets)
        return items
    
    def render_item(self, item):
        """ Renders an item using the template defined in its model's `timeline_template` attribute """
        template = getattr(item, 'timeline_template', None)
        if template:
            html = render_to_string(template, {'item'}, self.request) 
        else:
            if settings.DEBUG:
                raise ImproperlyConfigured('No `timeline_template` attribute found for item model "%s"' % item._meta.model)
            html = '<!-- Error: Timeline content for model "%s" could not be rendered.' % item._meta.model
        return html
    
    def _get_queryset_for_model(self, model):
        """ Returns a *sorted* queryset of items of a model for a user """
        queryset = self.fetch_queryset_for_user(model, self.user, sort_key=self.sort_key, only_mine=self.only_mine)
        if queryset is None:
            if settings.DEBUG:
                raise ImproperlyConfigured('No queryset could be matched for model "%s"' % model)
            return []
        return queryset
    
    def _mix_items_from_querysets(self, *streams):
        """ Will zip items from multiple querysts (each for a single model)
            into a single item list, while retainining an overall sort-order.
            Will peek all of the querysets and pick the next lowest-sorted item
            (honoring the given offset), until enough items for the page size are collected,
            or all querysets are exhausted. """
        # TODO
        # (we can assume each qs is sorted)
        
        # placeholder, just takes the first 10 of all qs
        cut_streams = [stream[:10] for stream in streams]
        reverse = '-' in self.sort_key
        sort_key = self.sort_key.replace('-', '')
        items = sorted(itertools.chain(*cut_streams), key=lambda item: getattr(item, sort_key), reverse=reverse) # placeholder
        return items
    
api_timeline = TimelineView.as_view()


