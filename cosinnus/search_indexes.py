# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from haystack import indexes

from cosinnus.utils.search import TemplateResolveCharField, TemplateResolveEdgeNgramField,\
    TagObjectSearchIndex
from cosinnus.utils.user import filter_active_users
from cosinnus.models.profile import get_user_profile_model
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety


class CosinnusGroupIndexMixin(object):
    
    def index_queryset(self, using=None):
        qs = self.get_model().objects.all()
        qs = qs.filter(is_active=True)
        qs = qs.select_related('media_tag').all()
        return qs


class CosinnusProjectIndex(CosinnusGroupIndexMixin, TagObjectSearchIndex, indexes.Indexable):
    
    text = TemplateResolveEdgeNgramField(document=True, use_template=True, template_name='search/indexes/cosinnus/cosinnusgroup_{field_name}.txt')
    rendered = TemplateResolveCharField(use_template=True, indexed=False, template_name='search/indexes/cosinnus/cosinnusgroup_{field_name}.txt')

    name = indexes.CharField(model_attr='name', boost=1.25)
    slug = indexes.CharField(model_attr='slug', indexed=False)
    public = indexes.BooleanField(model_attr='public')
    group_admins = indexes.MultiValueField(model_attr='admins', indexed=False)
    group_members = indexes.MultiValueField(model_attr='members', indexed=False)
    group_pendings = indexes.MultiValueField(model_attr='pendings', indexed=False)
    
    def get_model(self):
        return CosinnusProject
    
    
class CosinnusSocietyIndex(CosinnusGroupIndexMixin, TagObjectSearchIndex, indexes.Indexable):
    
    text = TemplateResolveEdgeNgramField(document=True, use_template=True, template_name='search/indexes/cosinnus/cosinnusgroup_{field_name}.txt')
    rendered = TemplateResolveCharField(use_template=True, indexed=False, template_name='search/indexes/cosinnus/cosinnusgroup_{field_name}.txt')

    name = indexes.CharField(model_attr='name', boost=1.25)
    slug = indexes.CharField(model_attr='slug', indexed=False)
    public = indexes.BooleanField(model_attr='public')
    group_admins = indexes.MultiValueField(model_attr='admins', indexed=False)
    group_members = indexes.MultiValueField(model_attr='members', indexed=False)
    group_pendings = indexes.MultiValueField(model_attr='pendings', indexed=False)
    
    def get_model(self):
        return CosinnusSociety


class UserProfileIndex(TagObjectSearchIndex, indexes.Indexable):
    text = TemplateResolveEdgeNgramField(document=True, use_template=True, template_name='search/indexes/cosinnus/userprofile_{field_name}.txt')
    rendered = TemplateResolveCharField(use_template=True, indexed=False, template_name='search/indexes/cosinnus/userprofile_{field_name}.txt')
    
    first_name = indexes.CharField(model_attr='user__first_name')
    last_name = indexes.CharField(model_attr='user__last_name')
    email = indexes.CharField(model_attr='user__email')
    
    get_absolute_url = indexes.CharField(model_attr='get_absolute_url', indexed=False)
    
    def get_model(self):
        return get_user_profile_model()

    def index_queryset(self, using=None):
        qs = self.get_model().objects.all()
        qs = filter_active_users(qs, filter_on_user_profile_model=True)
        qs = qs.select_related('user').all()
        return qs
    
    