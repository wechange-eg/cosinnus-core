# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from haystack.views import SearchView, search_view_factory

from cosinnus.forms.search import TaggableModelSearchForm
from cosinnus.views.user_dashboard import ModelRetrievalMixin
from django.views.generic.base import View
from django.http.response import HttpResponseForbidden, HttpResponseBadRequest,\
    JsonResponse
from cosinnus.utils.functions import is_number
from cosinnus.models.user_dashboard import DashboardItem
from cosinnus.models.map import SEARCH_MODEL_NAMES_REVERSE
from cosinnus.conf import settings
from django.core.exceptions import ImproperlyConfigured
import itertools
from cosinnus.utils.pagination import QuerysetLazyCombiner
import math
import logging
from django.db.models.query_utils import Q
import _functools
import operator

logger = logging.getLogger('cosinnus')


class TaggableSearchView(SearchView):
    
    results_per_page = 50

    def __call__(self, request):
        self.request = request
        self.form = self.build_form(form_kwargs=self.get_form_kwargs())
        self.query = self.get_query()
        self.results = self.get_results()
        return self.create_response()

    def get_form_kwargs(self):
        return {
            'request': self.request
        }


search = search_view_factory(TaggableSearchView,
    template='cosinnus/search.html',
    form_class=TaggableModelSearchForm,
)



class QuickSearchAPIView(ModelRetrievalMixin, View):
    
    http_method_names = ['get',]
    
    # which models can be displaed, as found in `SEARCH_MODEL_NAMES_REVERSE`
    content_types = ['polls', 'todos', 'files', 'pads', 'ideas', 'events', 'projects', 'groups',]
    
    if settings.COSINNUS_V2_DASHBOARD_SHOW_MARKETPLACE:
        content_types += ['offers']
    
    # which fields should be filtered for the query for each model
    content_type_filter_fields = {
        'polls': 'title',
        'todos': 'title',
        'files': 'title',
        'pads': 'title',
        'ideas': 'title',
        'events': 'title',
        'projects': 'name',
        'groups': 'name',
    }
    if settings.COSINNUS_V2_DASHBOARD_SHOW_MARKETPLACE:
        content_type_filter_fields['offers'] = 'title'
    
    
    # the key by which the timeline stream is ordered. must be present on *all* models
    sort_key = '-created'
    
    page_size = None
    default_page_size = 5
    min_page_size = 1
    max_page_size = 10
    
    filter_model = None # if set, only show items of this model
    user = None # set at initialization
    query = None # set at initialization
    query_terms = None # list, set at initialization
    
    
    def get(self, request, *args, **kwargs):
        """ Accepted GET-params: 
            `q` str: the query to search for
            `page_size` int (optional): Number of items to be returned. If a value larger than
                `self.max_page_size` is supplied, `self.max_page_size`is used instead.
                Default: `self.default_page_size`
        """
        self.user = request.user
        
        query = self.request.GET.get('q', '').strip()
        if not query:
            return HttpResponseBadRequest('Missing parameter: "q"!')
        self.query = query
        self.query_terms = self.query.lower().split(' ')
        
        self.page_size = int(request.GET.get('page_size', self.default_page_size))
        if not is_number(self.page_size):
            return HttpResponseBadRequest('Malformed parameter: "page_size": %s' % self.page_size)
        self.page_size = max(self.min_page_size, min(self.max_page_size, self.page_size))
        
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
             """
        rendered_items = [self.render_item(item) for item in items]
        response = {
            'items': rendered_items,
            'count': len(rendered_items),
        }
        return JsonResponse({'data': response})        
    
    def render_item(self, item):
        """ Renders an item to a dashboard item dict """
        return DashboardItem(item)
    
    def get_items(self):
        """ Returns a paginated list of items as mixture of different models, in sorted order """
        single_querysets = []
        for content_type in self.content_types:
            content_model = SEARCH_MODEL_NAMES_REVERSE.get(content_type, None)
            if content_model is None:
                if settings.DEBUG:
                    raise ImproperlyConfigured('Could not find content model for timeline content type "%s"' % content_type)
                continue
            single_querysets.append(self._get_queryset_for_model(content_model, self.content_type_filter_fields[content_type]))
                
        items = self._mix_items_from_querysets(*single_querysets)
        return items
    
    def _get_queryset_for_model(self, model, filter_field):
        """ Returns a *sorted* queryset of items of a model for a user, filtered by the query terms """
        queryset = self.fetch_queryset_for_user(model, self.user, sort_key=self.sort_key, only_mine=False)
        
        if queryset is None:
            if settings.DEBUG:
                raise ImproperlyConfigured('No queryset could be matched for model "%s"' % model)
            return []
        
        # filter the queryset to contain all of the query terms in their main title/name field
        expressions = [Q(**{'%s__icontains' % filter_field: term}) for term in self.query_terms]
        anded_expressions = _functools.reduce(operator.and_, expressions)
        queryset = queryset.filter(anded_expressions)
        return queryset
    
    def _mix_items_from_querysets(self, *streams):
        """ Will zip items from multiple querysts (each for a single model)
            into a single item list, while retainining an overall sort-order.
            Will peek all of the querysets and pick the next lowest-sorted item
            (honoring the given offset), until enough items for the page size are collected,
            or all querysets are exhausted. """
            
        reverse = '-' in self.sort_key
        
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

api_quicksearch = QuickSearchAPIView.as_view()
