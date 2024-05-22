# -*- coding: utf-8 -*-
"""
Created on 10.12.2013

@author: Sascha Narr
"""

from __future__ import unicode_literals

from django.shortcuts import render

from cosinnus.utils.renderer import BaseRenderer
from cosinnus_cloud.models import LinkedCloudFile


class LinkedCloudFileRenderer(BaseRenderer):
    model = LinkedCloudFile

    template = 'cosinnus_cloud/attached_cloud_files.html'
    template_v2 = 'cosinnus_cloud/v2/attached_cloud_files.html'
    template_single = 'cosinnus_cloud/single_cloud_file.html'
    template_list = None

    @classmethod
    def render(cls, context, objects, **kwargs):
        cloud_files = [
            linked_cloud_file.to_cloud_file(request=kwargs.get('request', None)) for linked_cloud_file in objects
        ]
        return super(LinkedCloudFileRenderer, cls).render(context, cloud_files, **kwargs)

    @classmethod
    def render_list_for_user(cls, user, request, qs_filter={}, limit=30, render_if_empty=True, **kwargs):
        """Will render a standalone list of items of the renderer's model for
        a user and a request (important if there are forms in the template).
        This function will filter for access permissions for all of the items,
        but any further filtering (group, organization, etc) will have to be
        passed via the qs_filter dict.
        """
        renderer = LinkedCloudFileRenderer()
        renderer.object_list = cls.get_object_list_for_user(user, qs_filter, limit=1000000)
        if not render_if_empty and not renderer.object_list:
            return None

        renderer.kwargs = {}
        context = {}
        context.update(kwargs)
        context['object_list'] = context['object_list'][:limit]
        context['objects'] = context['objects'][:limit]

        return render(request, cls.get_template_list(), context).content
