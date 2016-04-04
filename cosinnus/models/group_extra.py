# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import OrderedDict
import os
import re
import six

from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.core.validators import RegexValidator, MaxLengthValidator
from django.db import models
from django.db.models import Q
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _, pgettext_lazy as p_

from taggit.managers import TaggableManager

from cosinnus.conf import settings
from cosinnus.models.cms import CosinnusMicropage
from cosinnus.utils.functions import unique_aware_slugify,\
    clean_single_line_text
from cosinnus.utils.files import get_group_avatar_filename,\
    get_portal_background_image_filename, get_group_wallpaper_filename,\
    get_cosinnus_media_file_folder
from django.core.urlresolvers import reverse
from django.utils.functional import cached_property
from cosinnus.utils.urls import group_aware_reverse, get_domain_for_portal
from cosinnus.utils.compat import atomic
from cosinnus.core import signals
from cosinnus.core.registries.group_models import group_model_registry
from django.template.loader import render_to_string

from django.db import IntegrityError
from django.contrib import messages

import logging
import shutil
from easy_thumbnails.files import get_thumbnailer
from easy_thumbnails.exceptions import InvalidImageFormatError
from django.contrib.auth import get_user_model
from cosinnus.models.group import CosinnusGroupManager, CosinnusGroup,\
    get_cosinnus_group_model

logger = logging.getLogger('cosinnus')

class CosinnusProjectManager(CosinnusGroupManager):
    def get_queryset(self):
        return super(CosinnusProjectManager, self).get_queryset().filter(type=CosinnusGroup.TYPE_PROJECT)

    get_query_set = get_queryset




@python_2_unicode_compatible
class CosinnusProject(get_cosinnus_group_model()):
    
    class Meta:
        """ For some reason, the Meta isn't inherited automatically from CosinnusGroup here """
        proxy = True
        app_label = 'cosinnus'
        ordering = ('name',)
        verbose_name = _('Cosinnus project')
        verbose_name_plural = _('Cosinnus projects')
    
    GROUP_MODEL_TYPE = CosinnusGroup.TYPE_PROJECT
    
    objects = CosinnusProjectManager()
    
    def save(self, allow_type_change=False, *args, **kwargs):
        if not allow_type_change:
            self.type = CosinnusGroup.TYPE_PROJECT
        super(CosinnusProject, self).save(*args, **kwargs)
        
    def __str__(self):
        # FIXME: better caching for .portal.name
        return '%s (%s)' % (self.name, self.portal.name)

        
    
class CosinnusSocietyManager(CosinnusGroupManager):
    def get_queryset(self):
        return super(CosinnusSocietyManager, self).get_queryset().filter(type=CosinnusGroup.TYPE_SOCIETY)

    get_query_set = get_queryset


@python_2_unicode_compatible
class CosinnusSociety(get_cosinnus_group_model()):
    
    class Meta:
        """ For some reason, the Meta isn't inherited automatically from CosinnusGroup here """
        proxy = True        
        app_label = 'cosinnus'
        ordering = ('name',)
        verbose_name = _('Cosinnus group')
        verbose_name_plural = _('Cosinnus groups')
    
    GROUP_MODEL_TYPE = CosinnusGroup.TYPE_SOCIETY
    
    objects = CosinnusSocietyManager()
    
    def save(self, allow_type_change=False, *args, **kwargs):
        if not allow_type_change:
            self.type = CosinnusGroup.TYPE_SOCIETY
        super(CosinnusSociety, self).save(*args, **kwargs)
    
    def __str__(self):
        # FIXME: better caching for .portal.name
        return '%s (%s)' % (self.name, self.portal.name)

    
CosinnusGroup = get_cosinnus_group_model()
