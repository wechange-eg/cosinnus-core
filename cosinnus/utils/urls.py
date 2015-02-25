# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.utils.importlib import import_module
from django.db.models.loading import get_model

        
_group_aware_url_name = object() # late import because we cannot reference CosinnusGroup models here yet
_CosinnusGroup = None
def group_aware_reverse(viewname, urlconf=None, args=None, kwargs=None, prefix=None, current_app=None):
    """ CosinnusGroup.type aware, and Portal aware function that returns reverse URLs pointing
        to the correct Portal domain and the correct group type URL (society, project).
        
        WARNING:
        You MUST pass a group-object to kwargs['group'], not a slug, 
            if you want to use the function's Portal-awareness!
     """
    domain = ''
    if 'group' in kwargs:
        global _group_aware_url_name, _CosinnusGroup
        if not hasattr(_group_aware_url_name, '__call__'):
            _group_aware_url_name = import_module('cosinnus.templatetags.cosinnus_tags').group_aware_url_name
        if _CosinnusGroup is None: 
            _CosinnusGroup = get_model('cosinnus', 'CosinnusGroup')
        
        portal_id = None
        if issubclass(kwargs['group'].__class__, _CosinnusGroup):
            """ We accept a group object and swap it for its slug """
            group = kwargs['group']
            portal_id = group.portal_id
            domain = get_domain_for_portal(group.portal)
            kwargs['group'] = group.slug
        
        viewname = _group_aware_url_name(viewname, kwargs['group'], portal_id=portal_id)
    
    return domain + reverse(viewname, urlconf, args, kwargs, prefix, current_app)
        

def get_domain_for_portal(portal):
    # TODO FIXME: cache this!
    # FIXME: SSL (https://) secure support!
    return '%s%s' % ('http://' or 'https://', portal.site.domain)