# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging

from django.core.exceptions import MiddlewareNotUsed
from cosinnus.core import signals as cosinnus_signals
from django.db.models import signals
from django.utils.functional import curry
from django.http.response import HttpResponseRedirect
from django.utils.encoding import force_text
from cosinnus.conf import settings
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.db.models.loading import get_model

logger = logging.getLogger('cosinnus')

# delegate import to avoid cyclic dependencies
_CosinnusPortal = None

def CosinnusPortal():
    global _CosinnusPortal
    if _CosinnusPortal is None: 
        _CosinnusPortal = get_model('cosinnus', 'CosinnusPortal')
    return _CosinnusPortal

# delegate import to avoid cyclic dependencies
_CosinnusPermanentRedirect = None

def CosinnusPermanentRedirect():
    global _CosinnusPermanentRedirect
    if _CosinnusPermanentRedirect is None: 
        _CosinnusPermanentRedirect = get_model('cosinnus', 'CosinnusPermanentRedirect')
    return _CosinnusPermanentRedirect


startup_middleware_inited = False

class StartupMiddleware(object):
    """ This middleware will be run exactly once, after server startup, when all django
        apps are fully loaded. It is used to dispatch the all_cosinnus_apps_loaded signal.
    """
    
    def __init__(self):
        # check using a global var because this gets executed twice otherwise
        global startup_middleware_inited
        logger.info('Cosinnus.middleware.StartupMiddleware inited. (inited_before=%s)' % startup_middleware_inited)
        if not startup_middleware_inited:
            startup_middleware_inited = True
            cosinnus_signals.all_cosinnus_apps_loaded.send(sender=self)
        raise MiddlewareNotUsed


"""Adds the request to the instance of a Model that is being saved (created or modified)
   Taken from https://github.com/Atomidata/django-audit-log/blob/master/audit_log/middleware.py  and modified """
class AddRequestToModelSaveMiddleware(object):
    def process_request(self, request):
        if not request.method in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
            mark_request = curry(self.mark_request, request)
            signals.pre_save.connect(mark_request,  dispatch_uid = (self.__class__, request,), weak = False)

    def process_response(self, request, response):
        signals.pre_save.disconnect(dispatch_uid =  (self.__class__, request,))
        return response

    def mark_request(self, request, sender, instance, **kwargs):
        instance.request = request


GROUP_TYPES = None

class GroupPermanentRedirectMiddleware(object):
    """ This middleware checks if the group that is being accessed has an entry in the PermaRedirect
        table. If so, it redirects to the new group URL.
        This is used to make group URIs permanent after their type, slug, or portal changed.
        This table needs to be checked for unique_aware_slugify to prevent new groups re-taking old
        group slugs, effictively hiding the new groups under this redirect.
    """
    
    def process_request(self, request):
        # pokemon exception handling
        try:
            global GROUP_TYPES
            if GROUP_TYPES is None:
                from cosinnus.core.registries.group_models import group_model_registry
                GROUP_TYPES = [url_key for url_key in group_model_registry]
            
            request_tokens = request.build_absolute_uri().split('/')
            # if URL might be a link to a group
            if len(request_tokens) >= 5: 
                group_type = request_tokens[3]
                group_slug = request_tokens[4]
                if group_type in GROUP_TYPES:
                    to_group = CosinnusPermanentRedirect().get_group_for_pattern(CosinnusPortal().get_current(), group_type, group_slug)
                    if to_group:
                        # redirect to the redirect with HttpResponsePermanentRedirect
                        redirect_url = ''.join((to_group.get_absolute_url(), '/'.join(request_tokens[5:])))
                        messages.success(request, _('This group/project no longer resides under the URL you entered. You have been redirected automatically to the current location.'))
                        return HttpResponseRedirect(redirect_url)
        except Exception, e:
            if settings.DEBUG:
                raise
            logger.error('cosinnus.GroupPermanentRedirectMiddleware: Error while processing possible group redirect!', extra={'exception', force_text(e)})
                    