# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.exceptions import MiddlewareNotUsed
from cosinnus.core import signals as cosinnus_signals
from django.db.models import signals
from django.utils.functional import curry

startup_middleware_inited = False

class StartupMiddleware(object):
    """ This middleware will be run exactly once, after server startup, when all django
        apps are fully loaded. It is used to dispatch the all_cosinnus_apps_loaded signal.
    """
    
    def __init__(self):
        # check using a global var because this gets executed twice otherwise
        global startup_middleware_inited
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
