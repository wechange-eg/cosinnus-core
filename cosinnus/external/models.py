# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusBaseGroup

import logging
from cosinnus.models.mixins.indexes import IndexingUtilsMixin
from taggit.models import Tag
from django.core.validators import validate_comma_separated_integer_list
from django.db.models.query import QuerySet
logger = logging.getLogger('cosinnus')


class ExternalModelQuerySet(QuerySet):

    def count(self):
        return 0

    def all(self):
        return self.none()

    def filter(self, *args, **kwargs):
        return self.none()

    def exclude(self, *args, **kwargs):
        return self.none()

    def order_by(self, *ordering):
        return self.none()


class ExternalModelManager(models.Manager):
    
    def all(self):
        return ExternalModelQuerySet()
    

class ExternalObjectBaseModel(IndexingUtilsMixin, models.Model):
    """ Used for Haystack indexing of non-Databased map objects. 
        Index items by instantiating a subclass of this model and calling save() on it.
        
        Retrieve indexed items for the map by filtering for their model in a haystack
        SearchQuerySet. The aim of this base class is to always be compatible with both
        `HaystackMapCard` and `HaystackMapResult`.
    """
    
    source = models.CharField(max_length=255, null=False)
    # TODO: how to display external portals
    portal = models.IntegerField()
    
    """ from StoredDataIndexMixin """
    
    title = models.CharField(max_length=255, null=False)
    url = models.CharField(max_length=255, null=False)
    mt_location = models.CharField(max_length=255, null=False)
    mt_location_lat = models.FloatField(null=False)
    mt_location_lon = models.FloatField(null=False)
    
    # this is the id for the external object, most likely its url
    slug = models.CharField(max_length=255, null=False)
    description = models.TextField(blank=True, null=True)
    contact_info = models.TextField(blank=True, null=True)
    # the small icon image, should be a 144x144 image
    icon_image_url = models.CharField(max_length=255, blank=True, null=True)
    # the small background image or None, should be a 500x275 image
    background_image_small_url = models.CharField(max_length=255, blank=True, null=True)
    # the large background image or None, should be a 1000x550 image
    background_image_large_url = models.CharField(max_length=255, blank=True, null=True)
    # group slug for linking, subject to implementing indexed
    group_slug = models.CharField(max_length=255, blank=True, null=True)
    # group name for linking, subject to implementing indexed
    group_name = models.CharField(max_length=255, blank=True, null=True)
    # attendees for events, projects for groups
    participant_count = models.IntegerField(default=0)
    # member count for projects/groups, group-member count for events, memberships for users
    member_count = models.IntegerField(default=0)
    # groups/projects: number of upcoming events
    content_count = models.IntegerField(default=0)
    
    """ from DefaultTagObjectIndex """
    
    mt_tags = models.CharField(blank=True, null=True, max_length=255, 
        validators=[validate_comma_separated_integer_list])    
    mt_topics = models.CharField(blank=True, null=True, max_length=255,
        validators=[validate_comma_separated_integer_list])
    mt_visibility = models.IntegerField(default=2)
    mt_public = models.BooleanField(default=True)
    
    objects = ExternalModelManager()
    
    class Meta(object):
        managed = False
        
    def __init__(self, external_id, source, title, url, mt_location, mt_location_lat, mt_location_lon,
                 description=None, icon_image_url=None, contact_info=None, tags=[], topics=[]):
        """ Note:
            - `tags` is passed as an array of strings and then saved as taggit manager
            - `topics` is passed as an array of ints and then saved as comma-separated int string
                (see `settings.TOPIC_CHOICES`)
        """
        self.pk = url
        self.slug = external_id
        self.source = source
        self.title = title
        self.url = url
        self.mt_location = mt_location
        self.mt_location_lat = mt_location_lat
        self.mt_location_lon = mt_location_lon
        self.description = description
        self.icon_image_url = icon_image_url
        self.contact_info = contact_info
        self.mt_topics = ','.join((str(topic) for topic in topics))
        
        # add unknown tags to taggit, save all ids
        all_tags = []
        for str_tag in tags:
            try:
                tag = Tag.objects.get(name__iexact=str_tag)
            except Tag.DoesNotExist:
                tag = Tag.objects.create(name=str_tag)
            all_tags.append(str(tag.id))
        self.mt_tags = ','.join(all_tags)
        
        # fill all other fields' default values, or None (haystack needs this)
        self.portal = 0
        self.background_image_small_url = None
        self.background_image_large_url = None
        self.group_slug = None
        self.group_name = None
        self.participant_count = 0
        self.member_count = 0
        self.content_count = None
        self.mt_visibility = 2
        self.mt_public = True
    
    def save(self, *args, **kwargs):
        """ Only updates the haystack index for this instance, does not save anything to DB.
            Calling save() on any ExternalModel has this functionality. """
        self.update_index()
        
    
class ExternalBaseGroup(ExternalObjectBaseModel):
    
    GROUP_MODEL_TYPE = CosinnusBaseGroup.TYPE_PROJECT
    
    class Meta(object):
        managed = False

    def __init__(self, *args, **kwargs):
        super(ExternalBaseGroup, self).__init__(*args, **kwargs)
        self.type = self.GROUP_MODEL_TYPE
 
class ExternalProject(ExternalBaseGroup):
    
    GROUP_MODEL_TYPE = CosinnusBaseGroup.TYPE_PROJECT
    
    class Meta(object):
        managed = False
        
        
class ExternalSociety(ExternalBaseGroup):
    
    GROUP_MODEL_TYPE = CosinnusBaseGroup.TYPE_SOCIETY
    
    class Meta(object):
        managed = False
        
        