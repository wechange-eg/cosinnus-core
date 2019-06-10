# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic.base import TemplateView
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings
from cosinnus.views.map_api import get_searchresult_by_itemid


USER_MODEL = get_user_model()


def _generate_type_settings(types=[]):
    options = {
        'availableFilters': {
            'people': 'people' in types,
            'projects': 'projects' in types,
            'events': 'events' in types,
            'groups': 'groups' in types,
        },
        'activeFilters': {
            'people': 'people' in types,
            'projects': 'projects' in types,
            'events': 'events' in types,
            'groups': 'groups' in types,
        },
    }
    if settings.COSINNUS_IDEAS_ENABLED:
        options['availableFilters']['ideas'] = 'ideas' in types
        options['activeFilters']['ideas'] = 'ideas' in types
    return options
        
    

class BaseMapView(TemplateView):
    
    template_name = 'cosinnus/map/map_page.html'
    
    def get_page_title(self):
        """ Stub for overriding the HTML page title.
            @return: String or None for default. """
        return None
    
    def collect_map_options(self):
        return {
            'basePageUrl': self.request.path,
        }

    def get_context_data(self, **kwargs):
        ctx = {
            'skip_page_footer': True,
            'map_options_json': json.dumps(self.collect_map_options()),
            'page_title': self.get_page_title(),
        }
        item = self.request.GET.get('item', None)
        if item:
            ctx.update({
                'item': get_searchresult_by_itemid(item)
            })
        return ctx


class MapView(BaseMapView):

    def collect_map_options(self, **kwargs):
        options = super(MapView, self).collect_map_options(**kwargs)
        # for areas without a region, on the default map view, if the user has a location set up in his profile,
        # zoom them into their location-region to start out at
        settings = options.get('settings', {})
        if not self.request.user.is_anonymous\
                and not any([arg_check in self.request.GET for arg_check in ['ne_lat', 'ne_lon', 'sw_lat', 'sw_lon']])\
                and not getattr(settings, 'COSINNUS_MAP_OPTIONS', {}).get('geojson_region', None) :
            mt = self.request.user.cosinnus_profile.media_tag
            if mt.location_lat and mt.location_lon:
                settings.update({
                    'map': {
                        'location': [mt.location_lat, mt.location_lon],
                        'zoom': 9,
                    }
                })
        # apply GET params that are settings parameters and are
        # set once and then discarded (unlike the map/search query parameters)
        if self.request.GET.get('search_result_limit', None):
            settings.update({
                'searchResultLimit': self.request.GET.get('search_result_limit'),
            })
        if self.request.GET.get('filter_group', None):
            settings.update({
                'filterGroup': self.request.GET.get('filter_group'),
            })
        options.update({
            'settings': settings,
        })
        return options

map_view = MapView.as_view()


class TileView(BaseMapView):
    
    show_mine = False
    types = []
    
    def dispatch(self, request, *args, **kwargs):
        self.show_mine = kwargs.pop('show_mine', self.show_mine)
        self.types = kwargs.pop('types', self.types)
        return super(TileView, self).dispatch(request, *args, **kwargs)
    
    def collect_map_options(self, **kwargs):
        options = super(TileView, self).collect_map_options(**kwargs)
        
        _settings = _generate_type_settings(types=self.types)
        _settings.update({
            'showMine': self.show_mine,
        })
        options.update({
            'settings': _settings,
            'display': {
                'showMap': False,
                'showTiles': True,
                'tilesFullscreen': True,
                'showControls': True,
                'fullscreen': True,
                'routeNavigation': True
           }
        })
        return options
    
    def get_page_title(self):
        """ Depends on what types and/or "mine" page we show. """
        if self.types == ['projects']:
            if self.show_mine: 
                return _('My Projects')
            else:
                return _('Projects')
        if self.types == ['groups']:
            if self.show_mine: 
                return _('My Groups')
            else:
                return _('Groups')
        if self.types == ['ideas']:
            if self.show_mine: 
                return _('My Ideas')
            else:
                return _('Ideas')
        if self.types == ['people']:
            return _('People')
        
        return None
    
tile_view = TileView.as_view()


class MapEmbedView(TemplateView):
    """ An embeddable, resizable Map view without any other elements than the map """
    
    template_name = 'cosinnus/universal/map/map_embed.html'
    
    @method_decorator(xframe_options_exempt)
    def dispatch(self, *args, **kwargs):
        return super(MapEmbedView, self).dispatch(*args, **kwargs)

map_embed_view = MapEmbedView.as_view()

