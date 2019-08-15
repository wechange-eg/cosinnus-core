# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from haystack import indexes

from cosinnus.conf import settings
from cosinnus.utils.search import TemplateResolveCharField, TemplateResolveNgramField,\
    TagObjectSearchIndex, BOOSTED_FIELD_BOOST, StoredDataIndexMixin,\
    DocumentBoostMixin, CommaSeperatedIntegerMultiValueField,\
    LocalCachedIndexMixin, DEFAULT_BOOST_PENALTY_FOR_MISSING_IMAGE
from cosinnus.utils.user import filter_active_users, filter_portal_users
from cosinnus.models.profile import get_user_profile_model
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.contrib.auth import get_user_model
from cosinnus.utils.functions import normalize_within_stddev, resolve_class
from cosinnus.utils.group import get_cosinnus_group_model,\
    get_default_user_group_ids
from django.urls import reverse
from django.utils.functional import cached_property
from django.contrib.auth.models import AnonymousUser
from cosinnus.models.idea import CosinnusIdea
from cosinnus.models.tagged import LikeObject
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.timezone import now
from cosinnus.models.organization import CosinnusOrganization
from cosinnus.external.models import ExternalProject



class ExternalBaseIndexMixin(StoredDataIndexMixin, TagObjectSearchIndex,
         indexes.SearchIndex):
    
    # all of these fields will use the same-named object attribute through
    # a dynamic prepare() method
    MODEL_ATTR_FIELDS = []
    
    id = indexes.CharField()
    portal = indexes.IntegerField()
    
    """ from StoredDataIndexMixin """
    
    title = indexes.CharField(stored=True, indexed=False)
    # slug for linking
    slug = indexes.CharField(stored=True, indexed=True)
    url = indexes.CharField(stored=True, indexed=False)
    description = indexes.CharField(stored=True, indexed=False)
    # the small icon image, should be a 144x144 image
    icon_image_url = indexes.CharField(stored=True, indexed=False)
    # the small background image or None, should be a 500x275 image
    background_image_small_url = indexes.CharField(stored=True, indexed=False)
    # the large background image or None, should be a 1000x550 image
    background_image_large_url = indexes.CharField(stored=True, indexed=False)
    # group slug for linking, subject to implementing indexed
    group_slug = indexes.CharField(stored=True, indexed=True)
    # group name for linking, subject to implementing indexed
    group_name = indexes.CharField(stored=True, indexed=False)
    # attendees for events, projects for groups
    participant_count = indexes.IntegerField(stored=True, indexed=False)
    # member count for projects/groups, group-member count for events, memberships for users
    member_count = indexes.IntegerField(stored=True, indexed=False)
    # groups/projects: number of upcoming events
    content_count = indexes.IntegerField(stored=True, indexed=False)
    
    """ from DefaultTagObjectIndex """
        
    mt_location = indexes.CharField(model_attr='media_tag__location', null=True)
    mt_location_lat = indexes.FloatField(model_attr='media_tag__location_lat', null=True)
    mt_location_lon = indexes.FloatField(model_attr='media_tag__location_lon', null=True)
    mt_topics = CommaSeperatedIntegerMultiValueField(model_attr='media_tag__topics', null=True)
    mt_visibility = indexes.IntegerField(model_attr='media_tag__visibility', null=True)
    
    mt_public = indexes.BooleanField(model_attr='media_tag__public', null=True)


class ExternalProjectIndex(ExternalBaseIndexMixin, indexes.Indexable):
    
    def get_model(self):
        return ExternalProject


class ExternalSocietyIndex(ExternalBaseIndexMixin, indexes.Indexable):
    
    def get_model(self):
        return ExternalProject

    