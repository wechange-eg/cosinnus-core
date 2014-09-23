# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django.utils.importlib import import_module

from cosinnus.conf import settings
from cosinnus.core.registries.base import DictBaseRegistry


class GroupModelRegistry(DictBaseRegistry):

    def register(self, url_key, plural_url_key, url_name_prefix, model):
        self[url_key] = (plural_url_key, url_name_prefix, model)

    def get(self, url_key, default=None):
        _, _, model = super(GroupModelRegistry, self).get(url_key, (None, default))
        return self._resolve(url_key, model)
    
    def get_url_name_prefix(self, url_key, default=None):
        _, prefix, _ = super(GroupModelRegistry, self).get(url_key, (None, default))
        return prefix
    
    def get_plural_url_key(self, url_key, default=None):
        plural_url_key, _, _ = super(GroupModelRegistry, self).get(url_key, (default, None))
        return plural_url_key
    
    """
    def get_model_for_url_key(self, url_key):
        for m in settings.COSINNUS_ATTACHABLE_OBJECTS.get(url_key, []):
            if m in self:
                yield m
    """
    
    def _resolve(self, url_key, model):
        if isinstance(model, six.string_types):
            modulename, _, klass = model.rpartition('.')
            module = import_module(modulename)
            cls = getattr(module, klass, None)
            if cls is None:
                del self[url_key]
                raise ImportError("Cannot import cosinnus renderer %s from %s" % (
                    klass, model))
            else:
                self.register(url_key, cls)
                return cls
        else:
            return model

group_model_registry = GroupModelRegistry()


__all__ = ('group_model_registry', )

group_model_registry.register('project', 'projects', '', 'cosinnus.models.group.CosinnusProject')
group_model_registry.register('xxx', 'xxxs', 'xxx__', 'cosinnus.models.group.CosinnusSociety')
