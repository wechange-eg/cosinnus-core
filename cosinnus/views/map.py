# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.contrib.auth import get_user_model
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic.base import TemplateView

from cosinnus.templatetags.cosinnus_map_tags import get_map_marker_icon_settings_json
from cosinnus.views.map_api import get_searchresult_by_itemid


USER_MODEL = get_user_model()


class MapView(TemplateView):
    
    def collect_map_options(self):
        return {
            'basePageUrl': self.request.path,
        }

    def get_context_data(self, **kwargs):
        ctx = {
            'markers': get_map_marker_icon_settings_json(),
            'skip_page_footer': True,
            'map_options_json': json.dumps(self.collect_map_options())
        }
        item = self.request.GET.get('item', None)
        if item:
            ctx.update({
                'item': get_searchresult_by_itemid(item)
            })
        return ctx

    template_name = 'cosinnus/map/map_page.html'

map_view = MapView.as_view()


class TileProjectsView(MapView):

    def collect_map_options(self, **kwargs):
        options = super(TileProjectsView, self).collect_map_options(**kwargs)
        options.update({
            
        })
        return options

    template_name = 'cosinnus/map/map_page.html'

tile_projects_view = TileProjectsView.as_view()


class MapEmbedView(TemplateView):
    """ An embeddable, resizable Map view without any other elements than the map """
    
    template_name = 'cosinnus/universal/map/map_embed.html'
    
    @method_decorator(xframe_options_exempt)
    def dispatch(self, *args, **kwargs):
        return super(MapEmbedView, self).dispatch(*args, **kwargs)

map_embed_view = MapEmbedView.as_view()

