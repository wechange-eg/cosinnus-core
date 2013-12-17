# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import threading

from django.utils.datastructures import SortedDict
from django.utils.importlib import import_module

from cosinnus.conf import settings


class BaseRegistry(object):

    def __init__(self, module_name):
        self.discovered = False
        self.module_name = module_name
        self.modules = SortedDict()
        self.lock = threading.Lock()

    def autodiscover(self):
        with self.lock:
            if self.discovered:
                return
            self.discovered = True
            for app in settings.INSTALLED_APPS:
                if app in self.modules:
                    continue
                try:
                    module = import_module('%s.%s' % (app, self.module_name))
                    self.modules[app] = module
                    self.setup_actions(app, module)
                except ImportError:
                    continue

    def setup_actions(self, app, module):
        raise NotImplementedError('Subclasses of BaseRegistry must override this function.')
