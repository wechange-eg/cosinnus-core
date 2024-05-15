# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.core.validators import validate_comma_separated_integer_list
from django.db import models
from django.db.models.query import QuerySet
from taggit.models import Tag

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusBaseGroup
from cosinnus.models.mixins.indexes import IndexingUtilsMixin

logger = logging.getLogger('cosinnus')


class ExchangeModelQuerySet(QuerySet):
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


class ExchangeModelManager(models.Manager):
    def all(self):
        return ExchangeModelQuerySet()


class ExchangeObjectBaseModel(IndexingUtilsMixin, models.Model):
    """Used for Haystack indexing of non-Databased map objects.
    Index items by instantiating a subclass of this model and calling save() on it.

    Retrieve indexed items for the map by filtering for their model in a haystack
    SearchQuerySet. The aim of this base class is to always be compatible with both
    `HaystackMapCard` and `HaystackMapResult`.
    """

    id = models.CharField(max_length=255, primary_key=True)
    source = models.CharField(max_length=255, null=False)
    portal = models.IntegerField(default=settings.COSINNUS_EXCHANGE_PORTAL_ID)
    # defaults to public=True because external
    public = models.BooleanField(default=True)

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

    mt_tags = models.CharField(
        blank=True, null=True, max_length=255, validators=[validate_comma_separated_integer_list]
    )
    mt_topics = models.CharField(
        blank=True, null=True, max_length=255, validators=[validate_comma_separated_integer_list]
    )
    mt_visibility = models.IntegerField(default=2)
    mt_public = models.BooleanField(default=True)

    objects = ExchangeModelManager()

    class Meta(object):
        managed = False

    @property
    def pk(self):
        return self.id

    def _get_pk_val(self):
        return self.id

    def __init__(self, **kwargs):
        """Note:
        - `tags` is passed as an array of strings and then saved as taggit manager
        - `topics` is passed as an array of ints and then saved as comma-separated int string
            (see `settings.TOPIC_CHOICES`)
        """
        self.id = kwargs.get('url')
        self.slug = kwargs.get('external_id')
        self.source = kwargs.get('source')
        self.title = kwargs.get('title')
        self.url = kwargs.get('url')
        self.mt_location = kwargs.get('mt_location')
        self.mt_location_lat = kwargs.get('mt_location_lat')
        self.mt_location_lon = kwargs.get('mt_location_lon')
        self.description = kwargs.get('description')
        self.icon_image_url = kwargs.get('icon_image_url')
        self.contact_info = kwargs.get('contact_info')
        self.mt_topics = ','.join(str(t) for t in kwargs.get('mt_topics'))

        # add unknown tags to taggit, save all ids
        all_tags = []
        for str_tag in kwargs.get('mt_tags'):
            tag = Tag.objects.filter(name__iexact=str_tag).first()
            if not tag:
                tag = Tag.objects.create(name=str_tag)
            all_tags.append(str(tag.id))
        self.mt_tags = ','.join(all_tags)

        # fill all other fields' default values, or None (haystack needs this)
        self.background_image_small_url = None
        self.background_image_large_url = None
        self.group_slug = None
        self.group_name = None
        self.participant_count = 0
        self.member_count = 0
        self.content_count = None

    def save(self, *args, **kwargs):
        """Only updates the haystack index for this instance, does not save anything to DB.
        Calling save() on any ExchangeModel has this functionality."""
        self.update_index()


class ExchangeBaseGroup(ExchangeObjectBaseModel):
    GROUP_MODEL_TYPE = CosinnusBaseGroup.TYPE_PROJECT

    class Meta(object):
        managed = False

    def __init__(self, *args, **kwargs):
        super(ExchangeBaseGroup, self).__init__(*args, **kwargs)
        self.type = self.GROUP_MODEL_TYPE


class ExchangeProject(ExchangeBaseGroup):
    GROUP_MODEL_TYPE = CosinnusBaseGroup.TYPE_PROJECT

    class Meta(object):
        managed = False


class ExchangeSociety(ExchangeBaseGroup):
    GROUP_MODEL_TYPE = CosinnusBaseGroup.TYPE_SOCIETY

    class Meta(object):
        managed = False


class ExchangeConference(ExchangeBaseGroup):
    GROUP_MODEL_TYPE = CosinnusBaseGroup.TYPE_CONFERENCE

    class Meta(object):
        managed = False


class ExchangeOrganization(ExchangeObjectBaseModel):
    class Meta(object):
        managed = False


class ExchangeEvent(ExchangeObjectBaseModel):
    from_date = models.DateTimeField(max_length=255, blank=True, null=True)
    to_date = models.DateTimeField(max_length=255, blank=True, null=True)

    class Meta(object):
        managed = False

    def __init__(self, **kwargs):
        self.from_date = kwargs.pop('from_date', None)
        self.to_date = kwargs.pop('to_date', None)
        super().__init__(**kwargs)
