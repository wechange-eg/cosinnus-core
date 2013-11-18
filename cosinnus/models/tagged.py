# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from taggit.managers import TaggableManager
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings


class LocationModelMixin(models.Model):
    place = models.CharField(max_length=255)

    class Meta:
        abstract = True


class PeopleModelMixin(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        abstract = True


class BaseTagObject(LocationModelMixin, PeopleModelMixin):

    class Meta:
        abstract = True


class TagObject(BaseTagObject):

    class Meta:
        app_label = 'cosinnus'
        swappable = 'COSINNUS_TAG_OBJECT_MODEL'


class BaseTaggableObjectModel(models.Model):
    """
    Represents the base for all cosinnus main models. Each inheriting model
    has a set of simple ``tags`` which are just strings. Additionally each
    model has a ``media_tag`` that refers to all general tags like a location,
    people and so on.
    """

    tags = TaggableManager(_(u'Tags'), blank=True)
    media_tag = models.OneToOneField(settings.COSINNUS_TAG_OBJECT_MODEL)

    class Meta:
        abstract = True
