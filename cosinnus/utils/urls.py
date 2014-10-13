# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.utils.importlib import import_module

        
_group_aware_url_name = object() # late import because we cannot reference CosinnusGroup models here yet
def group_aware_reverse(viewname, urlconf=None, args=None, kwargs=None, prefix=None, current_app=None):
    if 'group' in kwargs:
        global _group_aware_url_name
        if not hasattr(_group_aware_url_name, '__call__'):
            _group_aware_url_name = import_module('cosinnus.templatetags.cosinnus_tags').group_aware_url_name
        
        viewname = _group_aware_url_name(viewname, kwargs['group'])
    return reverse(viewname, urlconf, args, kwargs, prefix, current_app)
        
