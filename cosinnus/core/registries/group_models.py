# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django.utils.importlib import import_module

from cosinnus.conf import settings
from cosinnus.core.registries.base import DictBaseRegistry
from django.core.exceptions import ImproperlyConfigured


class GroupModelRegistry(DictBaseRegistry):
    
    def _register(self, url_key, plural_url_key, url_name_prefix, model, form_model):
        self[url_key] = (plural_url_key, url_name_prefix, model, form_model)
    
    def register(self, url_key, plural_url_key, url_name_prefix, model, form_model):
        if url_key == plural_url_key:
            raise ImproperlyConfigured("You tried to register a group model with matching url_key and plural_url_key (%s, %s)!" % (url_key, plural_url_key))
        for _url_key in self:
            _plural_url_key, _url_name_prefix, _model, _form_model = super(GroupModelRegistry, self).get(_url_key, (None, None, None, None))
            if _plural_url_key == plural_url_key or _url_key == url_key or \
                _plural_url_key == url_key or _url_key == plural_url_key:
                raise ImproperlyConfigured("You tried to register a group model with url_keys (%s, %s) that already existed!" % (url_key, plural_url_key))
            if _model == model:
                raise ImproperlyConfigured("You tried to register a group model with a model (%s) that already existed!" % (model))
            if _form_model == form_model:
                raise ImproperlyConfigured("You tried to register a group form model with a model (%s) that already existed!" % (form_model))
        self._register(url_key, plural_url_key, url_name_prefix, model, form_model)
    
    def get_default_group_key(self):
        return self.__iter__().next()
    
    def get(self, url_key, default=None):
        plural_url_key, url_name_prefix, model, form_model = super(GroupModelRegistry, self).get(url_key, (None, None, default, None))
        return self._resolve(url_key, plural_url_key, url_name_prefix, model, form_model)[0]
    
    def get_by_plural_key(self, plural_url_key, default=None):
        for url_key in self:
            _plural_url_key, url_name_prefix, model, form_model = super(GroupModelRegistry, self).get(url_key, (None, None, default, None))
            if _plural_url_key == plural_url_key:
                return self._resolve(url_key, plural_url_key, url_name_prefix, model, form_model)[0]
        return default
    
    def get_form(self, url_key, default=None):
        plural_url_key, url_name_prefix, model, form_model = super(GroupModelRegistry, self).get(url_key, (None, None, default, None))
        return self._resolve(url_key, plural_url_key, url_name_prefix, model, form_model)[1]
    
    def get_form_by_plural_key(self, plural_url_key, default=None):
        for url_key in self:
            _plural_url_key, url_name_prefix, model, form_model = super(GroupModelRegistry, self).get(url_key, (None, None, default, None))
            if _plural_url_key == plural_url_key:
                return self._resolve(url_key, plural_url_key, url_name_prefix, model, form_model)[1]
        return default
    
    
    def get_url_name_prefix(self, url_key, default=None):
        _, prefix, _, _ = super(GroupModelRegistry, self).get(url_key, (None, default, None, None))
        return prefix
    
    def get_plural_url_key(self, url_key, default=None):
        plural_url_key, _, _, _ = super(GroupModelRegistry, self).get(url_key, (default, None, None, None))
        return plural_url_key
    
    """
    def get_model_for_url_key(self, url_key):
        for m in settings.COSINNUS_ATTACHABLE_OBJECTS.get(url_key, []):
            if m in self:
                yield m
    """
    
    def _resolve(self, url_key, plural_url_key, url_name_prefix, model, form_model):
        ret_model = None
        reg_cls = None
        if isinstance(model, six.string_types):
            modulename, _, klass = model.rpartition('.')
            module = import_module(modulename)
            cls = getattr(module, klass, None)
            if cls is None:
                del self[url_key]
                raise ImportError("Cannot import cosinnus renderer %s from %s" % (
                    klass, model))
            else:
                reg_cls = cls
                ret_model = cls
        else:
            ret_model = model
        
        ret_form_model = None
        reg_form_cls = None
        if isinstance(form_model, six.string_types):
            modulename, _, klass = form_model.rpartition('.')
            module = import_module(modulename)
            cls = getattr(module, klass, None)
            if cls is None:
                del self[url_key]
                raise ImportError("Cannot import cosinnus renderer %s from %s" % (
                    klass, form_model))
            else:
                reg_form_cls = cls
                ret_form_model = cls
        else:
            ret_form_model = form_model
            
        if reg_cls and reg_form_cls:
            self._register(url_key, plural_url_key, url_name_prefix, reg_cls, reg_form_cls)
            
        return (ret_model, ret_form_model)

group_model_registry = GroupModelRegistry()


__all__ = ('group_model_registry', )

group_model_registry.register('project', 'projects', '', 'cosinnus.models.group.CosinnusProject', 'cosinnus.forms.group._CosinnusProjectForm')
group_model_registry.register('group', 'groups', 'group__', 'cosinnus.models.group.CosinnusSociety', 'cosinnus.forms.group._CosinnusSocietyForm')
