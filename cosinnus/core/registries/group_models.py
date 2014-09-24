# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django.utils.importlib import import_module

from cosinnus.conf import settings
from cosinnus.core.registries.base import DictBaseRegistry
from django.core.exceptions import ImproperlyConfigured


class GroupModelRegistry(DictBaseRegistry):
    
    def _register(self, url_key, plural_url_key, url_name_prefix, model):
        self[url_key] = (plural_url_key, url_name_prefix, model)
    
    def register(self, url_key, plural_url_key, url_name_prefix, model):
        if url_key == plural_url_key:
            raise ImproperlyConfigured("You tried to register a group model with matching url_key and plural_url_key (%s, %s)!" % (url_key, plural_url_key))
        for _url_key in self:
            _plural_url_key, _url_name_prefix, _model = super(GroupModelRegistry, self).get(_url_key, (None, None, None))
            
            if _plural_url_key == plural_url_key or _url_key == url_key or \
                _plural_url_key == url_key or _url_key == plural_url_key:
                raise ImproperlyConfigured("You tried to register a group model with url_keys (%s, %s) that already existed!" % (url_key, plural_url_key))
            if _model == model:
                raise ImproperlyConfigured("You tried to register a group model with a model (%s) that already existed!" % (model))
        self._register(url_key, plural_url_key, url_name_prefix, model)
    
    def get_default_group_key(self):
        return self.__iter__().next()
    
    def get(self, url_key, default=None):
        plural_url_key, url_name_prefix, model = super(GroupModelRegistry, self).get(url_key, (None, None, default))
        return self._resolve(url_key, plural_url_key, url_name_prefix, model)
    
    def get_by_plural_key(self, plural_url_key, default=None):
        for url_key in self:
            _plural_url_key, url_name_prefix, model = super(GroupModelRegistry, self).get(url_key, (None, None, default))
            if _plural_url_key == plural_url_key:
                return self._resolve(url_key, plural_url_key, url_name_prefix, model)
        return default
    
    
    def get_url_name_prefix(self, url_key, default=None):
        _, prefix, _ = super(GroupModelRegistry, self).get(url_key, (None, default, None))
        return prefix
    
    def get_plural_url_key(self, url_key, default=None):
        plural_url_key, _, _ = super(GroupModelRegistry, self).get(url_key, (default, None, None))
        return plural_url_key
    
    """
    def get_model_for_url_key(self, url_key):
        for m in settings.COSINNUS_ATTACHABLE_OBJECTS.get(url_key, []):
            if m in self:
                yield m
    """
    
    def _resolve(self, url_key, plural_url_key, url_name_prefix, model):
        if isinstance(model, six.string_types):
            modulename, _, klass = model.rpartition('.')
            module = import_module(modulename)
            cls = getattr(module, klass, None)
            if cls is None:
                del self[url_key]
                raise ImportError("Cannot import cosinnus renderer %s from %s" % (
                    klass, model))
            else:
                self._register(url_key, plural_url_key, url_name_prefix, cls)
                return cls
        else:
            return model

group_model_registry = GroupModelRegistry()


__all__ = ('group_model_registry', )

group_model_registry.register('project', 'projects', '', 'cosinnus.models.group.CosinnusProject')
group_model_registry.register('group', 'groups', 'group__', 'cosinnus.models.group.CosinnusSociety')
