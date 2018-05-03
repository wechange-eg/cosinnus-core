# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.urlresolvers import reverse, NoReverseMatch
from django.utils.importlib import import_module
from django.db.models.loading import get_model

from cosinnus.conf import settings
from django.core.cache import cache
from django.utils.http import is_safe_url
from cosinnus.utils.group import get_cosinnus_group_model
import re
import urlparse

BETTER_URL_RE = re.compile(ur'(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:\'".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))')
    

        
_PORTAL_PROTOCOL_CACHE_KEY = 'cosinnus/core/portal/%d/protocol'
        
_group_aware_url_name = object() # late import because we cannot reference CosinnusGroup models here yet
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


def urlEncodeNonAscii(b):
    return re.sub('[\x80-\xFF]', lambda c: '%%%02x' % ord(c.group(0)), b)

def iriToUri(iri):
    """ Properly encodes any url string to a safe URL """
    parts= urlparse.urlparse(iri)
    return urlparse.urlunparse(
        part.encode('idna') if parti==1 else urlEncodeNonAscii(part.encode('utf-8'))
        for parti, part in enumerate(parts)
    )
