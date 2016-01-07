# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from haystack import indexes

from cosinnus.models.group import CosinnusGroup
from cosinnus.utils.search import TagObjectSearchIndex, TemplateResolveCharField,\
    TemplateResolveEdgeNgramField


class GroupIndex(TagObjectSearchIndex, indexes.Indexable):
    text = TemplateResolveEdgeNgramField(document=True, use_template=True)
    rendered = TemplateResolveCharField(use_template=True, indexed=False)

    name = indexes.CharField(model_attr='name', boost=1.25)
    slug = indexes.CharField(model_attr='slug', indexed=False)
    public = indexes.BooleanField(model_attr='public')
    admins = indexes.MultiValueField(model_attr='admins', indexed=False)
    members = indexes.MultiValueField(model_attr='members', indexed=False)
    pendings = indexes.MultiValueField(model_attr='pendings', indexed=False)

    def get_model(self):
        return CosinnusGroup

    def index_queryset(self, using=None):
        qs = self.get_model().objects.all()
        qs = qs.filter(is_active=True)
        qs = qs.select_related('media_tag').all()
        return qs


class TagObjectIndex(indexes.SearchIndex):
    mt_location = indexes.CharField(model_attr='media_tag__location', null=True)
    mt_location_lat = indexes.FloatField(model_attr='media_tag__location_lat', null=True)
    mt_location_lon = indexes.FloatField(model_attr='media_tag__location_lon', null=True)
    mt_place = indexes.CharField(model_attr='media_tag__place', null=True)
    mt_valid_start = indexes.DateTimeField(model_attr='media_tag__valid_start', null=True)
    mt_valid_end = indexes.DateTimeField(model_attr='media_tag__valid_end', null=True)
    mt_approach = indexes.CharField(model_attr='media_tag__approach', null=True)
    mt_topics = indexes.MultiValueField(model_attr='media_tag__topics', null=True)
    mt_persons = indexes.MultiValueField(null=True)
    mt_likes = indexes.IntegerField(model_attr='media_tag__likes', null=True)
    mt_visibility = indexes.BooleanField(model_attr='media_tag__visibility', null=True)

    def prepare_mt_persons(self, obj):
        if obj.media_tag:
            return prepare_users(obj.media_tag.persons.all())


from cosinnus.utils.search import prepare_users
