# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.datastructures import SortedDict

from cosinnus.core.loaders.registry import BaseRegistry
from django.core.exceptions import ImproperlyConfigured


class AppRegistry(BaseRegistry):

    app_names = SortedDict()
    app_labels = SortedDict()
    # dict of model names to the name of cosinnus app that provides it
    attachable_objects_models = SortedDict()
    # dict of renderer Classes that implement <render_attached_objects(context, files)>
    attachable_object_renderers = SortedDict()
    
    _attach_model_field = 'ATTACHABLE_OBJECT_MODELS'
    _attach_renderers_field = 'ATTACHABLE_OBJECT_RENDERERS'

    def setup_actions(self, app, module):
        name = getattr(module, 'COSINNUS_APP_NAME', app)
        self.app_names[app] = name

        label = getattr(module, 'COSINNUS_APP_LABEL', None)
        self.app_labels[app] = label or name.title()
        
        renderers = getattr(module, self._attach_renderers_field, None)
        if renderers:
            self.attachable_object_renderers.update(renderers)
        
        attach_model_list = getattr(module, self._attach_model_field, [])
        for model in attach_model_list:
            if not model in renderers:
                raise ImproperlyConfigured("Cosinnus app '%s' provides attachable object model '%s' in '%s', but doesn't provide a Renderer for it. Configure one in cosinnus_app.%s!" % 
                                           (app, model, self._attach_model_field, self._attach_renderers_field))
            self.attachable_objects_models[model] = app
        

cosinnus_app_registry = AppRegistry('cosinnus_app')
