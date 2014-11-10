# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.core.exceptions import MiddlewareNotUsed
from cosinnus.core import signals


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
            signals.all_cosinnus_apps_loaded.send(sender=self)
        raise MiddlewareNotUsed
