# -*- coding: utf-8 -*-
"""
Created on 10.12.2013

@author: Sascha Narr
"""
from __future__ import unicode_literals

from cosinnus.utils.renderer import BaseRenderer
from cosinnus_file.models import FileEntry
from cosinnus.views.mixins.hierarchy import HierarchicalListCreateViewMixin
from django.shortcuts import render


class FileEntryRenderer(HierarchicalListCreateViewMixin, BaseRenderer):
    
    model = FileEntry

    template = 'cosinnus_file/attached_files.html'
    template_v2 = 'cosinnus_file/v2/attached_files.html'
    template_single = 'cosinnus_file/single_file.html'
    template_list = 'cosinnus_file/file_list_standalone.html'
    
    
    @classmethod
    def render(cls, context, myobjs, **kwargs):
        files = []
        images = []
        for fileobj in myobjs:
            if fileobj.is_image:
                images.append(fileobj)
            else:
                files.append(fileobj)
        return super(FileEntryRenderer, cls).render(context, files=files, images=images, all_files=files+images, **kwargs)
    
    
    @classmethod
    def render_list_for_user(cls, user, request, qs_filter={}, limit=30, render_if_empty=True, **kwargs):
        """ Will render a standalone list of items of the renderer's model for
            a user and a request (important if there are forms in the template).
            This function will filter for access permissions for all of the items,
            but any further filtering (group, organization, etc) will have to be
            passed via the qs_filter dict.
        """
        renderer = FileEntryRenderer()
        renderer.object_list = cls.get_object_list_for_user(user, qs_filter, limit=1000000)
        if not render_if_empty and (not renderer.object_list or \
            len(renderer.object_list)==1 and renderer.object_list[0].is_container):
            return None
        
        renderer.kwargs = {}
        context = HierarchicalListCreateViewMixin.get_context_data(renderer)
        context.update(kwargs)
        context['object_list'] = context['object_list'][:limit]
        context['objects'] = context['objects'][:limit]
        
        return render(request, cls.get_template_list(), context).content
