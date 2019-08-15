# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from haystack import indexes

from cosinnus.conf import settings
from cosinnus.external.models import ExternalProject, ExternalSociety
from cosinnus.utils.search import CommaSeperatedIntegerMultiValueField, TemplateResolveNgramField


EXTERNAL_CONTENT_PORTAL_ID = 99999


class ExternalBaseIndexMixin(indexes.SearchIndex):
    
    source = indexes.CharField(stored=True, indexed=False, model_attr='source')
    portal = indexes.IntegerField(default=EXTERNAL_CONTENT_PORTAL_ID)
    location = indexes.LocationField(null=True)
    
    """ from StoredDataIndexMixin """
    
    title = indexes.CharField(stored=True, indexed=False, model_attr='title')
    # slug for linking
    slug = indexes.CharField(stored=True, indexed=True, model_attr='slug')
    url = indexes.CharField(stored=True, indexed=False, model_attr='url')
    description = indexes.CharField(stored=True, indexed=False, model_attr='description')
    # the small icon image, should be a 144x144 image
    icon_image_url = indexes.CharField(stored=True, indexed=False, model_attr='icon_image_url')
    # the small background image or None, should be a 500x275 image
    background_image_small_url = indexes.CharField(stored=True, indexed=False, model_attr='background_image_small_url', null=True)
    # the large background image or None, should be a 1000x550 image
    background_image_large_url = indexes.CharField(stored=True, indexed=False, model_attr='background_image_large_url', null=True)
    # group slug for linking, subject to implementing indexed
    group_slug = indexes.CharField(stored=True, indexed=True, model_attr='group_slug', null=True)
    # group name for linking, subject to implementing indexed
    group_name = indexes.CharField(stored=True, indexed=False, model_attr='group_name', null=True)
    # attendees for events, projects for groups
    participant_count = indexes.IntegerField(stored=True, indexed=False, model_attr='participant_count', null=True)
    # member count for projects/groups, group-member count for events, memberships for users
    member_count = indexes.IntegerField(stored=True, indexed=False, model_attr='member_count', null=True)
    # groups/projects: number of upcoming events
    content_count = indexes.IntegerField(stored=True, indexed=False, model_attr='content_count', null=True)
    
    """ from DefaultTagObjectIndex """
        
    mt_location = indexes.CharField(stored=True, indexed=False, null=True, model_attr='mt_location')
    mt_location_lat = indexes.FloatField(null=True, model_attr='mt_location_lat')
    mt_location_lon = indexes.FloatField(null=True, model_attr='mt_location_lon')
    mt_topics = CommaSeperatedIntegerMultiValueField(null=True, model_attr='mt_topics')
    mt_visibility = indexes.IntegerField(stored=True, indexed=False, default=2)
    
    mt_public = indexes.BooleanField(default=True)
    
    text = TemplateResolveNgramField(document=True, model_attr='title')
    
    def prepare_location(self, obj):
        if obj.mt_location_lat and obj.mt_location_lon:
            # this expects (lat,lon)!
            return "%s,%s" % (obj.mt_location_lat, obj.mt_location_lon)
        return None

class ExternalBaseGroupIndex(ExternalBaseIndexMixin, indexes.SearchIndex):
    # for filtering on this model
    is_group_model = indexes.BooleanField(default=True)
    always_visible = indexes.BooleanField(default=True)
    public = indexes.BooleanField(default=True)


class ExternalProjectIndex(ExternalBaseGroupIndex, indexes.Indexable):
    
    def get_model(self):
        return ExternalProject


class ExternalSocietyIndex(ExternalBaseGroupIndex, indexes.Indexable):
    
    def get_model(self):
        return ExternalSociety

    