# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse, NoReverseMatch
from importlib import import_module
from django.apps import apps

from cosinnus.conf import settings
from django.core.cache import cache
from django.utils.http import is_safe_url
from cosinnus.utils.group import get_cosinnus_group_model
import re
import urllib.parse

BETTER_URL_RE = re.compile(r'(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’])|(?:(?<!. -@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))', re.IGNORECASE)
BETTER_EMAIL_RE = re.compile(r'[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*', re.IGNORECASE)  # domain
    

        
_PORTAL_PROTOCOL_CACHE_KEY = 'cosinnus/core/portal/%d/protocol'
        
_group_aware_url_name = object() # late import because we cannot reference CosinnusGroup models here yet
_CosinnusPortal = None
def group_aware_reverse(viewname, urlconf=None, args=None, kwargs=None, prefix=None, current_app=None, skip_domain=False):
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
        global _group_aware_url_name
        if not hasattr(_group_aware_url_name, '__call__'):
            _group_aware_url_name = import_module('cosinnus.templatetags.cosinnus_tags').group_aware_url_name
        
        portal_id = None
        if issubclass(kwargs['group'].__class__, get_cosinnus_group_model()):
            """ We accept a group object and swap it for its slug """
            group = kwargs['group']
            portal_id = group.portal_id
            domain = get_domain_for_portal(group.portal)
            kwargs['group'] = group.slug
        else:
            group = kwargs['group']
        
        viewname = _group_aware_url_name(viewname, group, portal_id=portal_id)
    else:
        global _CosinnusPortal
        if _CosinnusPortal is None: 
            _CosinnusPortal = apps.get_model('cosinnus', 'CosinnusPortal')
        domain = get_domain_for_portal(_CosinnusPortal.get_current())
    
    # NOTE: this used to be: reverse(viewname, urlconf, args, kwargs, prefix, current_app) in Django 1.8
    # we simply removed the prefix arg as it should still work
    return ('' if skip_domain else domain) + reverse(viewname, urlconf, args, kwargs, current_app)
        

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


def get_non_cms_root_url(request=None):
    """ Tries to get a safe non-cms root URL to redirect to.
        If the new user dashboard is enabled, will use that.
        Else, will attempt the stream activity page. If cosinnus_stream is not installed,
        will redirect to the projects page. """
    if getattr(settings, 'COSINNUS_USE_V2_DASHBOARD', False) or \
        (getattr(settings, 'COSINNUS_USE_V2_DASHBOARD_ADMIN_ONLY', False) and request and request.user.is_superuser):
        return reverse('cosinnus:user-dashboard')
    else:
        try:
            return reverse('cosinnus:my_stream')
        except NoReverseMatch:
            return reverse('cosinnus:group-list')


def safe_redirect(url, request):
    """ Will return the supplied URL if it is safe or a safe wechange root URL """
    # Ensure the user-originating redirection url is safe.
    if not is_safe_url(url=url, allowed_hosts=[request.get_host()]):
        url = get_non_cms_root_url(request)
    return url


def urlEncodeNonAscii(b):
    return re.sub('[\x80-\xFF]', lambda c: '%%%02x' % ord(c.group(0)), b)

def iriToUri(iri):
    """ Properly encodes any url string to a safe URL """
    parts= urllib.parse.urlparse(iri)
    return urllib.parse.urlunparse(
        part.encode('idna') if parti==1 else urlEncodeNonAscii(part.encode('utf-8'))
        for parti, part in enumerate(parts)
    )

def redirect_next_or(request_with_next, alternate_url):
    """ Checks the given request if it contains a ?next= param, and if that is a safe url returns it.
        Otherwise, returns `alternate_url` """
    next_param = request_with_next.GET.get('next', None)
    if not next_param or not is_safe_url(next_param, allowed_hosts=[request_with_next.get_host()]):
        return alternate_url
    return next_param

def redirect_with_next(url, request_with_next):
    """ Checks the given request if it contains a ?next= param, and if that is a safe url,
        attaches to the given url a "?next=<next_url>" fragment.
        Otherwise, returns `url` """
    next_param = request_with_next.GET.get('next', None)
    if not next_param or not is_safe_url(next_param, allowed_hosts=[request_with_next.get_host()]):
        return url
    return '%s?next=%s' % (url, next_param) 
    