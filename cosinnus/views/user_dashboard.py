# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import inspect
import itertools
import json
import logging
import math

from annoying.functions import get_object_or_None
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.db.models.query_utils import Q
from django.http.response import JsonResponse, HttpResponseForbidden, \
    HttpResponseBadRequest
from django.template.loader import render_to_string
from django.views.generic import TemplateView
from django.views.generic.base import View
import six

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
from cosinnus.models.idea import CosinnusIdea
from cosinnus.models.map import SEARCH_MODEL_NAMES_REVERSE
from cosinnus.models.tagged import LikeObject, BaseTaggableObjectModel, \
    BaseHierarchicalTaggableObjectModel, BaseTagObject, LastVisitedObject
from cosinnus.models.user_dashboard import DashboardItem
from cosinnus.utils.dates import timestamp_from_datetime, \
    datetime_from_timestamp
from cosinnus.utils.filters import exclude_special_folders
from cosinnus.utils.functions import is_number
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.pagination import QuerysetLazyCombiner
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user
from cosinnus.views.mixins.group import RequireLoggedInMixin
from cosinnus.views.mixins.reflected_objects import MixReflectedObjectsMixin
from django.shortcuts import redirect
from cosinnus.views.ui_prefs import get_ui_prefs_for_user
from django.utils.timezone import now
from dateutil.relativedelta import relativedelta


logger = logging.getLogger('cosinnus')


class UserDashboardView(RequireLoggedInMixin, TemplateView):
    
    template_name = 'cosinnus/v2/dashboard/user_dashboard.html'
    
    def get(self, request, *args, **kwargs):
        if not(getattr(settings, 'COSINNUS_USE_V2_DASHBOARD', False) or (getattr(settings, 'COSINNUS_USE_V2_DASHBOARD_ADMIN_ONLY', False) and request.user.is_superuser)):
            return redirect('cosinnus:map')
        return super(UserDashboardView, self).get(request, *args, **kwargs)
    
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
            'ui_prefs': get_ui_prefs_for_user(self.request.user),
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


class MyGroupsClusteredMixin(object):
    
    def get_group_clusters(self, user, sort_by_activity=False):
        clusters = []
        projects = list(CosinnusProject.objects.get_for_user(user))
        societies = list(CosinnusSociety.objects.get_for_user(user))
        group_ct = ContentType.objects.get_for_model(get_cosinnus_group_model())
        if sort_by_activity:
            group_last_visited_qs = LastVisitedObject.objects.filter(user=user, content_type=group_ct, portal=CosinnusPortal.get_current())
            # a dict of group-id -> datetime
            group_last_visited = dict(group_last_visited_qs.values_list('object_id', 'visited'))
        else:
            group_last_visited = {}
        default_date = now() - relativedelta(years=100)
        
        class AttrList(list):
            last_visited = None
        
        filter_group_slugs = getattr(settings, 'NEWW_DEFAULT_USER_GROUPS', [])
        for society in societies:
            if society.slug in filter_group_slugs:
                continue
            
            # the most recent visit time to any project or society in the cluster
            most_recent_dt = group_last_visited.get(society.id, default_date)
            items = AttrList([DashboardItem(society, is_emphasized=True)])
            for i in range(len(projects)-1, -1, -1):
                project = projects[i]
                if project.parent == society:
                    items.append(DashboardItem(project))
                    projects.pop(i)
                    project_dt = group_last_visited.get(project.id, default_date)
                    most_recent_dt = project_dt if project_dt > most_recent_dt else most_recent_dt
            items.last_visited = most_recent_dt
            clusters.append(items)
            
        # add unclustered projects as own cluster
        for proj in projects:
            items = AttrList([DashboardItem(proj)])
            items.last_visited = group_last_visited.get(proj.id, default_date)
            clusters.append(items)
        
        # sort clusters by last_visited
        if sort_by_activity:
            clusters = sorted(clusters, key=lambda cluster: cluster.last_visited, reverse=True)
        
        return clusters


class GroupWidgetView(MyGroupsClusteredMixin, BaseUserDashboardWidgetView):
    """ Shows (for now) unlimited, all projects clustered by groups of a user.
        TODO: implement sorting by last accessed
        TODO: implement limiting to 3 projects per group and n total items.
        TODO: use clever caching """
        
    def get_data(self, *kwargs):
        clusters = self.get_group_clusters(self.request.user, sort_by_activity=True)
        return {'group_clusters': clusters}

api_user_groups = GroupWidgetView.as_view()


class LikedIdeasWidgetView(BaseUserDashboardWidgetView):
    """ Shows all unlimited (for now) ideas the user likes. """
    
    def get_data(self, *kwargs):
        idea_ct = ContentType.objects.get_for_model(CosinnusIdea)
        likeobjects = LikeObject.objects.filter(user=self.request.user, content_type=idea_ct, liked=True) 
        liked_ideas_ids = likeobjects.values_list('object_id', flat=True)
        liked_ideas = CosinnusIdea.objects.all_in_portal().filter(id__in=liked_ideas_ids)
        ideas = [DashboardItem(idea) for idea in liked_ideas]
        return {'items': ideas}

api_user_liked_ideas = LikedIdeasWidgetView.as_view()


class ModelRetrievalMixin(object):
    """ Mixin for all dashboard views requiring content data """
    
    def fetch_queryset_for_user(self, model, user, sort_key=None, only_mine=True, only_mine_strict=True, current_only=True):
        """ Retrieves a queryset of sorted content items for a user, for a given model.
            @param model: An actual model class. Supported are all `BaseTaggableObjectModel`s,
                `CosinnusIdea`, and `postman.Message`
            @param user: Querysets are filtered by view permission for this user
            @param sort_key: (optional) the key for the `order_by` clause for the queryset
            @param only_mine: if True, will only show objects that belong to groups or projects
                the `user` is a member of, including the Forum, and including Ideas.
                If False, will include all visible items in this portal for the user. 
            @param only_mine_strict: If set to True along with `only_mine`, really only objects
                from the user's groups and projects will be returned, *excluding* the Forum and
                Ideas.
            @param current_only: if True, will only retrieve current items (ie, upcoming events) 
                TODO: is this correct?
        """
        
        ct = ContentType.objects.get_for_model(model)
        model_name = '%s.%s' % (ct.app_label, ct.model_class().__name__)
        
        # ideas are excluded in strict mode
        if model is CosinnusIdea and only_mine and only_mine_strict:
            return model.objects.none()
        
        queryset = None
        skip_filters = False
        if BaseHierarchicalTaggableObjectModel in inspect.getmro(model):
            queryset = model._default_manager.filter(is_container=False)
            queryset = exclude_special_folders(queryset)
        elif model_name == 'cosinnus_event.Event' and current_only:
            queryset = model.objects.all_upcoming()
        elif model_name == 'cosinnus_marketplace.Offer':
            queryset = model.objects.all_active()
        elif model is CosinnusIdea or BaseTaggableObjectModel in inspect.getmro(model):
            queryset = model._default_manager.all()
        elif model_name == "postman.Message":
            queryset = model.objects.inbox(user)
            skip_filters = True
        elif model is get_cosinnus_group_model() or issubclass(model, get_cosinnus_group_model()):
            queryset = model.objects.get_queryset()
        else:
            return None
    
        assert queryset is not None
        if not skip_filters:
            # mix in reflected objects
            if model_name.lower() in settings.COSINNUS_REFLECTABLE_OBJECTS and \
                        BaseTaggableObjectModel in inspect.getmro(model):
                mixin = MixReflectedObjectsMixin()
                queryset = mixin.mix_queryset(queryset, model, None, user)
            
            portal_id = CosinnusPortal.get_current().id
            portal_list = [portal_id]
            if False:
                # include all other portals in pool
                portal_list += getattr(settings, 'COSINNUS_SEARCH_DISPLAY_FOREIGN_PORTALS', [])
            
            if model is CosinnusIdea or model is get_cosinnus_group_model() or issubclass(model, get_cosinnus_group_model()):
                queryset = queryset.filter(portal__id__in=portal_list)
            else:
                queryset = queryset.filter(group__portal__id__in=portal_list)
                user_group_ids = get_cosinnus_group_model().objects.get_for_user_pks(user)
                
                # in strict mode, filter any content from the default groups as well
                if only_mine and only_mine_strict:
                    exclude_slugs = getattr(settings, 'NEWW_DEFAULT_USER_GROUPS', [])
                    if exclude_slugs:
                        exclude_groups = get_cosinnus_group_model().objects.get_cached(slugs=exclude_slugs, portal_id=portal_id)
                        exclude_group_ids = [group.id for group in exclude_groups]
                        user_group_ids = [group_id for group_id in user_group_ids if group_id not in exclude_group_ids]
                filter_q = Q(group__pk__in=user_group_ids)
                # if the switch is on, also include public posts from all portals
                if not only_mine:
                    filter_q = filter_q | Q(media_tag__visibility=BaseTagObject.VISIBILITY_ALL)
                queryset = queryset.filter(filter_q)
    
                # filter for read permissions for user
                queryset = filter_tagged_object_queryset_for_user(queryset, user)
            
            if sort_key:
                queryset = queryset.order_by(sort_key)
            else:
                queryset = queryset.order_by('-created')
        return queryset
    

class TypedContentWidgetView(ModelRetrievalMixin, BaseUserDashboardWidgetView):
    """ Shows BaseTaggable content for the user """
    
    model = None
    # if True: will show only content that the user has recently visited
    # if False: will show all of the users content, sorted by creation date
    show_recent = False
    
    default_page_size = 3
    min_page_size = 1
    max_page_size = 20
    
    # if given, will only return items *older* than the given timestamp!
    offset_timestamp = None
    default_offset_timestamp = None
    
    def get(self, request, *args, **kwargs):
        self.show_recent = kwargs.pop('show_recent', False)
        
        content = kwargs.pop('content', None)
        if not content:
            return HttpResponseBadRequest('No content type supplied')
        self.model = SEARCH_MODEL_NAMES_REVERSE.get(content, None)
        if not self.model:
            return HttpResponseBadRequest('Unknown content type supplied: "%s"' % content)
        
        self.page_size = int(request.GET.get('page_size', self.default_page_size))
        if not is_number(self.page_size):
            return HttpResponseBadRequest('Malformed parameter: "page_size": %s' % self.page_size)
        self.page_size = max(self.min_page_size, min(self.max_page_size, self.page_size))
        
        self.offset_timestamp = request.GET.get('offset_timestamp', self.default_offset_timestamp)
        if self.offset_timestamp is not None and not is_number(self.offset_timestamp):
            return HttpResponseBadRequest('Malformed parameter: "offset_timestamp"')
        if self.offset_timestamp is not None and isinstance(self.offset_timestamp, six.string_types):
            self.offset_timestamp = float(self.offset_timestamp)
        
        return super(TypedContentWidgetView, self).get(request, *args, **kwargs)
    
    def get_data(self, **kwargs):
        has_more = False
        offset_timestamp = None
        
        if self.show_recent:
            # showing "last-visited" content, ordering by visit datetime
            ct = ContentType.objects.get_for_model(self.model)
            queryset = LastVisitedObject.objects.filter(content_type=ct, user=self.request.user, portal=CosinnusPortal.get_current())
            queryset = queryset.order_by('-visited')
            
            # cut off at timestamp if given
            if self.offset_timestamp:
                offset_datetime = datetime_from_timestamp(self.offset_timestamp)
                queryset = queryset.filter(visited__lt=offset_datetime)
        
            # calculate has_more and new offset timestamp
            has_more = queryset.count() > self.page_size
            queryset = queryset[:self.page_size]
            # the `item_data` field already contains the JSON of `DashboardItem`
            items = list(queryset.values_list('item_data', flat=True))
            
            queryset = list(queryset)
            if len(queryset) > 0:
                offset_timestamp = timestamp_from_datetime(queryset[-1].visited)
        else:
            # all content, ordered by creation date
            only_mine = True
            sort_key = '-created' 
            queryset = self.fetch_queryset_for_user(self.model, self.request.user, sort_key=sort_key, only_mine=only_mine)
            if queryset is None:
                return {'items':[], 'widget_title': '(error: %s)' % self.model.__name__}
            
            # cut off at timestamp if given
            if self.offset_timestamp:
                offset_datetime = datetime_from_timestamp(self.offset_timestamp)
                queryset = queryset.filter(created__lt=offset_datetime)
        
            # calculate has_more and new offset timestamp
            has_more = queryset.count() > self.page_size
            queryset = list(queryset[:self.page_size])
            if len(queryset) > 0:
                offset_timestamp = timestamp_from_datetime(queryset[-1].created)
            
            items = [DashboardItem(item, user=self.request.user) for item in queryset]
            
        return {
            'items': items,
            'widget_title': self.model._meta.verbose_name_plural,
            'has_more': has_more,
            'offset_timestamp': offset_timestamp,
        }

api_user_typed_content = TypedContentWidgetView.as_view()



class TimelineView(ModelRetrievalMixin, View):
    """ Timeline view for a user.
        Returns items as rendered HTML. 
        Accepts content type filters and pagination parameters. """
    
    http_method_names = ['get',]
    
    # which models can be displaed, as found in `SEARCH_MODEL_NAMES_REVERSE`
    content_types = ['polls', 'todos', 'files', 'pads', 'ideas', 'events', 'notes',]
    
    if settings.COSINNUS_V2_DASHBOARD_SHOW_MARKETPLACE:
        content_types += ['offers']
    
    # the key by which the timeline stream is ordered. must be present on *all* models
    sort_key = '-last_action'
    
    page_size = None
    default_page_size = 10
    min_page_size = 1
    max_page_size = 200
    
    # if given, will only return items *older* than the given timestamp!
    offset_timestamp = None
    default_offset_timestamp = None
    
    only_mine = None
    only_mine_default = False
    
    filter_model = None # if set, only show items of this model
    user = None # set at initialization
    
    
    def get(self, request, *args, **kwargs):
        """ Accepted GET-params: 
            `page_size` int (optional): Number of items to be returned. If a value larger than
                `self.max_page_size` is supplied, `self.max_page_size`is used instead.
                Default: `self.default_page_size`
            `offset_timestamp` float (optional): If supplied, only items older than the given 
                timestamp are returned. Items with the exact timestamp are excluded.
                Use this parameter in conjunction with the return value `last_timestamp` for 
                pagination.
            `only_mine` bool (optional): if True, will only show objects that belong to groups 
                or projects the `user` is a member of.  If False, will include all visible items 
                in this portal for the user.
        """
        # require authenticated user
        self.user = request.user
        if not request.user.is_authenticated:
            return HttpResponseForbidden('Not authenticated.')
        content = kwargs.pop('content', None)
        if content:
            self.filter_model = SEARCH_MODEL_NAMES_REVERSE.get(content, None)
            if not self.filter_model:
                return HttpResponseBadRequest('Unknown content type supplied: "%s"' % content)
        
        self.page_size = int(request.GET.get('page_size', self.default_page_size))
        if not is_number(self.page_size):
            return HttpResponseBadRequest('Malformed parameter: "page_size": %s' % self.page_size)
        self.page_size = max(self.min_page_size, min(self.max_page_size, self.page_size))
        
        self.offset_timestamp = request.GET.get('offset_timestamp', self.default_offset_timestamp)
        if self.offset_timestamp is not None and not is_number(self.offset_timestamp):
            return HttpResponseBadRequest('Malformed parameter: "offset_timestamp"')
        if self.offset_timestamp is not None and isinstance(self.offset_timestamp, six.string_types):
            self.offset_timestamp = float(self.offset_timestamp)
            
        self.only_mine = request.GET.get('only_mine', self.only_mine_default)
        if isinstance(self.only_mine, six.string_types):
            self.only_mine = bool(json.loads(self.only_mine))
        
        items = self.get_items()
        response = self.render_to_response(items)
        return response
    
    def render_to_response(self, items):
        """ Renders a list of items and returns a JsonResponse with the items 
            and additional meta info.
            Returned data:
            @return: 
                `items`: list[str]: a list of rendered html items
                `count` int: count of the number of rendered items
                `has_more` bool: if more items are potentially available
                `last_timestamp` float: the timestamp of the oldest returned item. 
                    used as offset for the next paginated request. Will be None
                    if 0 items were returned. 
             """
        rendered_items = [self.render_item(item) for item in items]
        last_timestamp = None
        if len(items) > 0:
            last_timestamp = timestamp_from_datetime(getattr(items[-1], self.sort_key_natural))
        response = {
            'items': rendered_items,
            'count': len(rendered_items),
            'has_more': len(rendered_items) == self.page_size,
            'last_timestamp': last_timestamp,
        }
        return JsonResponse({'data': response})        
    
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
            context = {'item': item}
            html = render_to_string(template, context, self.request) 
        else:
            if settings.DEBUG:
                raise ImproperlyConfigured('No `timeline_template` attribute found for item model "%s"' % item._meta.model)
            html = '<!-- Error: Timeline content for model "%s" could not be rendered.' % item._meta.model
        return html
    
    def _get_queryset_for_model(self, model):
        """ Returns a *sorted* queryset of items of a model for a user """
        # the only_mine mode here is a only_mine_strict!
        queryset = self.fetch_queryset_for_user(model, self.user, sort_key=self.sort_key, only_mine=self.only_mine, only_mine_strict=self.only_mine)
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
            
        reverse = '-' in self.sort_key
        # apply timestamp offset
        if self.offset_timestamp:
            offset_datetime = datetime_from_timestamp(self.offset_timestamp)
            streams = [stream.filter(**{'%s__lt' % self.sort_key_natural: offset_datetime}) for stream in streams]
        
        if not getattr(settings, 'COSINNUS_V2_DASHBOARD_USE_NAIVE_FETCHING', False):
            queryset_iterator = QuerysetLazyCombiner(streams, self.sort_key_natural, math.ceil(self.page_size/2.0), reverse=reverse)
            items = list(itertools.islice(queryset_iterator, self.page_size)) 
        else:    
            logger.warn('Using naive queryset picking! Performance may suffer in production!')
            # naive just takes `page_size` items from each stream, then sorts and takes first `page_size` items
            cut_streams = [stream[:self.page_size] for stream in streams]
            items = sorted(itertools.chain(*cut_streams), key=lambda item: getattr(item, self.sort_key_natural), reverse=reverse) # placeholder
            items = items[:self.page_size]
            
        return items
    
    @property
    def sort_key_natural(self):
        """ Returns the sort_key without '-' """
        return self.sort_key.replace('-', '')
    
api_timeline = TimelineView.as_view()


