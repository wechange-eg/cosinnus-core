# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.datastructures import SortedDict

from cosinnus.core.loaders.registry import BaseRegistry


class AppRegistry(BaseRegistry):

    app_names = SortedDict()
    app_labels = SortedDict()

    def setup_actions(self, app, module):
        name = getattr(module, 'COSINNUS_APP_NAME', app)
        self.app_names[app] = name

        label = getattr(module, 'COSINNUS_APP_LABEL', None)
        self.app_labels[app] = label or name.title()

cosinnus_app_registry = AppRegistry('cosinnus_app')
