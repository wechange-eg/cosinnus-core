# -*- coding: utf-8 -*-
"""
Created on 08.07.2014

@author: Sascha Narr
"""
from __future__ import unicode_literals

from cosinnus.utils.renderer import BaseRenderer


class TodoEntryRenderer(BaseRenderer):

    template = 'cosinnus_todo/attached_todos.html'
    template_v2 = 'cosinnus_todo/v2/attached_todos.html'
    template_single = 'cosinnus_todo/single_todo.html'

    @classmethod
    def render(cls, context, myobjs, **kwargs):
        return super(TodoEntryRenderer, cls).render(context, todos=myobjs, **kwargs)
