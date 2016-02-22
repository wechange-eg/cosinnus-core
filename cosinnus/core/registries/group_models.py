# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django.utils.importlib import import_module

from cosinnus.conf import settings
from cosinnus.core.registries.base import DictBaseRegistry
from django.core.exceptions import ImproperlyConfigured


class GroupModelRegistry(DictBaseRegistry):
    """
        Registry for different Group models extending CosinnusGroup.
        These models are different types of Groups that all have the common functionality
        to house group-specific cosinnus apps and group BaseTaggableObject items together.
        
        Using this you can register for example a basic Project that can contain items, 
        as well as a MemberGroup for just a few members or an Organization for lots of members.
        Each of these types of Group will have their own URLs with their specific URL fragment
        preceeding them to seperate them. 
        
        Also, all defined URL names for URL matching are prefixed with their registered prefix 
        so it is possible to target a specific group type using a URL. This happens in the 
        Cosinnus URL registry based on the CosinnusGroup types registered with group_model_registry.
        
        # Example:
        We register two CosinnusGroup types:
            - A Project with url-fragment 'project', plural fragment 'projects' and prefix ''
            - A Group with url-fragemnt 'group', plural fragment 'groups' and prefix 'group__'
        
        To point to the overview page of a group you would then form a URL using its prefix in the URL name.
            - {% url 'cosinnus:group__group-list-map' %} 
            - (will lead to http://localhost:8000/groups/)
        instead of for a project (because of the '' prefix)
            - {% url 'cosinnus:group-list-map' %}
            - (will lead to http://localhost:8000/projects/)
        
        To point to a page within any CosinnusGroup, no matter its type, use the cosinnus_tag 'group_url':
            - {% group_url 'cosinnus:group-dashboard' group=group as group_url %}
            - will lead to either http://localhost:8000/group/<group_slug>/microsite/ or
                http://localhost:8000/project/<group_slug>/microsite/, depending on which type of group
                the group with the passed slug is.
    """
    
    
    group_type_index = {} 
    
    def _register(self, url_key, plural_url_key, url_name_prefix, model, form_model):
        self[url_key] = (plural_url_key, url_name_prefix, model, form_model)
    
    def register(self, url_key, plural_url_key, url_name_prefix, model, form_model, type_index):
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
        
        self.group_type_index[type_index] = url_key
        self._register(url_key, plural_url_key, url_name_prefix, model, form_model)
    
    def get_url_key_by_type(self, type_index):
        return self.group_type_index[type_index]
    
    def get_by_type(self, type_index):
        return self.get(self.group_type_index[type_index], None)
    
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
    
    def get_url_name_prefix_by_type(self, group_type, default=None):
        _, prefix, _, _ = super(GroupModelRegistry, self).get(self.group_type_index[group_type], (None, default, None, None))
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

# schema for registering a new group model and its URL paths:
#group_model_registry.register(<group-url-fragment>, '<plural-url-fragment>', '<django url-name-prefix>', '<str group model name>', '<str group form>', <int group type>)
group_model_registry.register('project', 'projects', '', 'cosinnus.models.group_extra.CosinnusProject', 'cosinnus.forms.group._CosinnusProjectForm', 0) # CosinnusGroup.TYPE_PROJECT
group_model_registry.register('group', 'groups', 'group__', 'cosinnus.models.group_extra.CosinnusSociety', 'cosinnus.forms.group._CosinnusSocietyForm', 1) # CosinnusGroup.TYPE_SOCIETY
