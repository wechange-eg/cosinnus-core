# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.datastructures import SortedDict

from cosinnus.core.loaders.registry import BaseRegistry
from django.core.exceptions import ImproperlyConfigured
from cosinnus.conf import settings
'''
Created on 11.12.2013

@author: Sascha
'''
        
class AttachedObjectRegistry(BaseRegistry):
    
    # dict of model names to the name of cosinnus app that provides it
    attachable_objects_models = SortedDict()
    # dict of renderer Classes that implement <render_attached_objects(context, files)>
    attachable_object_renderers = SortedDict()
    # which objects may be attached to which? (defined in settings.py)
    attachable_to = {}
    
    _attach_model_field = 'ATTACHABLE_OBJECT_MODELS'
    _attach_renderers_field = 'ATTACHABLE_OBJECT_RENDERERS'

    def setup_actions(self, app, module):
        renderers = getattr(module, self._attach_renderers_field, None)
        if renderers:
            self.attachable_object_renderers.update(renderers)
        
        attach_model_list = getattr(module, self._attach_model_field, [])
        for model in attach_model_list:
            if not model in renderers:
                raise ImproperlyConfigured("Cosinnus app '%s' provides attachable object model '%s' in '%s', but doesn't provide a Renderer for it. Configure one in cosinnus_app.%s!" % 
                                           (app, model, self._attach_model_field, self._attach_renderers_field))
            self.attachable_objects_models[model] = app
            
        # use configured attachability and filter out not-provided models
        self.attachable_to = dict(settings.COSINNUS_ATTACHABLE_OBJECTS)
        for model_from, modellist in self.attachable_to.items():
            self.attachable_to[model_from] = [modelval for modelval in modellist if modelval in self.attachable_objects_models]
        
cosinnus_attached_object_registry = AttachedObjectRegistry('cosinnus_app')