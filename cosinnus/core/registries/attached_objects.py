# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django.utils.importlib import import_module

from cosinnus.conf import settings
from cosinnus.core.registries.base import DictBaseRegistry


class AttachedObjectRegistry(DictBaseRegistry):

    def register(self, model, renderer):
        with self.lock:
            if model in settings.COSINNUS_ATTACHABLE_OBJECTS:
                self[model] = renderer

    def get(self, key, default=None):
        with self.lock:
            renderer = super(AttachedObjectRegistry, self).get(key, default)
            return self._resolve(key, renderer)

    def get_attachable_to(self, model):
        with self.lock:
            for model in settings.COSINNUS_ATTACHABLE_OBJECTS.get(model, []):
                if model in self:
                    yield model

    def _resolve(self, model, renderer):
        with self.lock:
            if isinstance(renderer, six.string_types):
                modulename, _, klass = renderer.rpartition('.')
                module = import_module(modulename)
                cls = getattr(module, klass, None)
                if cls is None:
                    del self[model]
                    raise ImportError("Cannot import cosinnus renderer %s from %s" % (
                        klass, renderer))
                else:
                    self.register(model, cls)
                    return cls
            else:
                return renderer

attached_object_registry = AttachedObjectRegistry()


__all__ = ('attached_object_registry', )
