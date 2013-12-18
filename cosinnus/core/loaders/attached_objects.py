# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django.utils.datastructures import SortedDict
from django.utils.importlib import import_module

from cosinnus.core.loaders.registry import BaseRegistry
from django.core.exceptions import ImproperlyConfigured
from cosinnus.conf import settings


class AttachedObjectRegistry(BaseRegistry):
    #: dict of model names to the name of cosinnus app that provides it
    attachable_objects_models = SortedDict()

    #: dict of renderer Classes that implement <render_attached_objects(context, files)>
    attachable_object_renderers = SortedDict()

    #: which objects may be attached to which? (defined in settings.py)
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
                raise ImproperlyConfigured(
                    "Cosinnus app '%s' provides attachable object model '%s' "
                    "in '%s', but doesn't provide a Renderer for it. Configure"
                    " one in cosinnus_app.%s!" % (
                        app, model, self._attach_model_field,
                        self._attach_renderers_field
                    )
                )
            self.attachable_objects_models[model] = app

        # use configured attachability and filter out not-provided models
        self.attachable_to = dict(settings.COSINNUS_ATTACHABLE_OBJECTS)
        for model_from, modellist in six.iteritems(self.attachable_to):
            self.attachable_to[model_from] = [
                modelval for modelval in modellist if modelval in self.attachable_objects_models
            ]

    def get_renderer(self, model_name):
        renderer = self.attachable_object_renderers.get(model_name, None)
        if isinstance(renderer, six.string_types):
            modulename, _, klass = renderer.rpartition('.')
            module = import_module(modulename)
            renderer = getattr(module, klass, None)
            if renderer:
                self.attachable_object_renderers[model_name] = renderer
            else:
                del self.attachable_object_renderers[model_name]
        return renderer

cosinnus_attached_object_registry = AttachedObjectRegistry('cosinnus_app')
