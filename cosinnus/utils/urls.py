# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.urlresolvers import reverse, NoReverseMatch
from django.utils.importlib import import_module
from django.db.models.loading import get_model

from cosinnus.conf import settings
from django.core.cache import cache
from django.utils.http import is_safe_url
        
_PORTAL_PROTOCOL_CACHE_KEY = 'cosinnus/core/portal/%d/protocol'
        
_group_aware_url_name = object() # late import because we cannot reference CosinnusGroup models here yet
_CosinnusGroup = None
_CosinnusPortal = None
def group_aware_reverse(viewname, urlconf=None, args=None, kwargs=None, prefix=None, current_app=None):
    """ CosinnusGroup.type aware, and Portal aware function that returns reverse URLs pointing
        to the correct Portal domain and the correct group type URL (society, project).
        
        NOTE:
        This will return a full URL, including protocol:
            ex.: http://wachstumswende.de/group/Blog/note/list/
        
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
    else:
        global _CosinnusPortal
        if _CosinnusPortal is None: 
            _CosinnusPortal = get_model('cosinnus', 'CosinnusPortal')
        domain = get_domain_for_portal(_CosinnusPortal.get_current())
    
    return domain + reverse(viewname, urlconf, args, kwargs, prefix, current_app)
        

def get_domain_for_portal(portal):
    """ We obtain the protocol from either the DB Portal entry, or, if not set there,
        from the setting `COSINNUS_SITE_PROTOCOL` or default to 'http' 
        The domain comes from the Portal's Site. """
    
    domain = cache.get(_PORTAL_PROTOCOL_CACHE_KEY % portal.id)
    if not domain:
        protocol = portal.protocol or getattr(settings, 'COSINNUS_SITE_PROTOCOL', 'http')
        domain = '%s://%s' % (protocol, portal.site.domain)
        cache.set(_PORTAL_PROTOCOL_CACHE_KEY % portal.id, domain) # 5 minutes is okay here
    return domain


def get_non_cms_root_url():
    """ Tries to get a safe non-cms root URL to redirect to.
        Will attempt the stream activity page first. If cosinnus_stream is not installed,
        will redirect to the projects page. """
    try:
        return reverse('cosinnus:my_stream')
    except NoReverseMatch:
        return reverse('cosinnus:group-list')


def safe_redirect(url, request):
    """ Will return the supplied URL if it is safe or a safe wechange root URL """
    # Ensure the user-originating redirection url is safe.
    if not is_safe_url(url=url, host=request.get_host()):
        url = get_non_cms_root_url()
    return url
