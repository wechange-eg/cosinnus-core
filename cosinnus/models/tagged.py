# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from taggit.managers import TaggableManager
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings
from cosinnus.models import CosinnusGroup
from cosinnus.utils.functions import unique_aware_slugify


class LocationModelMixin(models.Model):
    place = models.CharField(max_length=255)

    class Meta:
        abstract = True


class PeopleModelMixin(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        abstract = True


class PublicModelMixin(models.Model):
    public = models.BooleanField(_('Public'), default=False)

    class Meta:
        abstract = True


@python_2_unicode_compatible
class BaseTagObject(LocationModelMixin, PeopleModelMixin, PublicModelMixin):

    class Meta:
        abstract = True

    def __str__(self):
        return "Tag object {0}".format(self.pk)


class TagObject(BaseTagObject):

    class Meta:
        app_label = 'cosinnus'
        swappable = 'COSINNUS_TAG_OBJECT_MODEL'


class AttachedObject(models.Model):
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    target_object = generic.GenericForeignKey('content_type', 'object_id')
    
    class Meta:
        app_label = 'cosinnus'
        ordering = ('content_type',)
        unique_together = (('content_type', 'object_id'),)
        verbose_name = _('Attached object')
        verbose_name_plural = _('Attached objects')
    
    def __str__(self):
        return '<attach: %s::%s>' % (self.content_type, self.object_id)
    

@python_2_unicode_compatible
class BaseTaggableObjectModel(models.Model):
    """
    Represents the base for all cosinnus main models. Each inheriting model
    has a set of simple ``tags`` which are just strings. Additionally each
    model has a ``media_tag`` that refers to all general tags like a location,
    people and so on.
    """

    tags = TaggableManager(_('Tags'), blank=True)
    media_tag = models.OneToOneField(settings.COSINNUS_TAG_OBJECT_MODEL,
        blank=True, null=True, on_delete=models.PROTECT)
    
    attached_objects = models.ManyToManyField(AttachedObject, blank=True, null=True)
    
    group = models.ForeignKey(CosinnusGroup, verbose_name=_('Group'),
        related_name='%(app_label)s_%(class)s_set', on_delete=models.PROTECT)

    title = models.CharField(_('Title'), max_length=255)
    slug = models.SlugField(max_length=55)  # human readable part is 50 chars

    class Meta:
        abstract = True
        unique_together = (('group', 'slug'),)

    def __str__(self):
        return "Tagged object {0}".format(self.pk)

    def save(self, *args, **kwargs):
        unique_aware_slugify(self, 'title', 'slug', group=self.group)
        super(BaseTaggableObjectModel, self).save(*args, **kwargs)
