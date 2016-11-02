# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from haystack import indexes

from cosinnus.utils.search import TemplateResolveCharField, TemplateResolveEdgeNgramField,\
    TagObjectSearchIndex, BOOSTED_FIELD_BOOST
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

    boosted = indexes.CharField(model_attr='name', boost=BOOSTED_FIELD_BOOST)

    group_members = indexes.MultiValueField(model_attr='members', indexed=False)
    public = indexes.BooleanField(model_attr='public')
    always_visible = indexes.BooleanField(default=True)
    
    def get_model(self):
        return CosinnusProject
    
    def prepare(self, obj):
        """ Boost all objects of this type """
        data = super(CosinnusProjectIndex, self).prepare(obj)
        data['boost'] = 1.25
        return data
    
    
class CosinnusSocietyIndex(CosinnusGroupIndexMixin, TagObjectSearchIndex, indexes.Indexable):
    
    text = TemplateResolveEdgeNgramField(document=True, use_template=True, template_name='search/indexes/cosinnus/cosinnusgroup_{field_name}.txt')
    rendered = TemplateResolveCharField(use_template=True, indexed=False, template_name='search/indexes/cosinnus/cosinnusgroup_{field_name}.txt')

    boosted = indexes.CharField(model_attr='name', boost=BOOSTED_FIELD_BOOST)
    
    group_members = indexes.MultiValueField(model_attr='members', indexed=False)
    public = indexes.BooleanField(model_attr='public')
    always_visible = indexes.BooleanField(default=True)
    
    def get_model(self):
        return CosinnusSociety
    
    def prepare(self, obj):
        """ Boost all objects of this type """
        data = super(CosinnusSocietyIndex, self).prepare(obj)
        data['boost'] = 1.25
        return data


class UserProfileIndex(TagObjectSearchIndex, indexes.Indexable):
    text = TemplateResolveEdgeNgramField(document=True, use_template=True, template_name='search/indexes/cosinnus/userprofile_{field_name}.txt')
    rendered = TemplateResolveCharField(use_template=True, indexed=False, template_name='search/indexes/cosinnus/userprofile_{field_name}.txt')
    
    boosted = indexes.CharField(model_attr='get_full_name', boost=BOOSTED_FIELD_BOOST)
    
    user_visibility_mode = indexes.BooleanField(default=True) # switch to filter differently on mt_visibility
    membership_groups = indexes.MultiValueField(model_attr='cosinnus_groups_pks') # ids of all groups the user is member/admin of
    
    
    def get_model(self):
        return get_user_profile_model()

    def index_queryset(self, using=None):
        qs = self.get_model().objects.all()
        qs = filter_active_users(qs, filter_on_user_profile_model=True)
        qs = qs.select_related('user').all()
        return qs
    
    def prepare(self, obj):
        """ Boost all objects of this type """
        data = super(UserProfileIndex, self).prepare(obj)
        data['boost'] = 1.5
        return data
    
    