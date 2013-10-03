# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.utils.translation import ugettext_lazy as _

from taggit.managers import TaggableManager


class TaggableModel(models.Model):

    tags = TaggableManager(_('Tags'), blank=True)

    class Meta:
        abstract = True
