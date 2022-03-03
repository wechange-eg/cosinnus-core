# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
import logging

from annoying.functions import get_object_or_None
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings
from cosinnus_event.utils.bbb_streaming import trigger_streamer_status_changes
from cosinnus.models.group import CosinnusGroupManager, CosinnusGroup, \
    get_cosinnus_group_model
from cosinnus.trans.group import get_group_trans_by_type


logger = logging.getLogger('cosinnus')


class CosinnusProjectManager(CosinnusGroupManager):
    def get_queryset(self):
        return super(CosinnusProjectManager, self).get_queryset().filter(type=CosinnusGroup.TYPE_PROJECT)

    get_query_set = get_queryset

    
class CosinnusSocietyManager(CosinnusGroupManager):
    def get_queryset(self):
        return super(CosinnusSocietyManager, self).get_queryset().filter(type=CosinnusGroup.TYPE_SOCIETY)

    get_query_set = get_queryset
    
    
class CosinnusConferenceManager(CosinnusGroupManager):
    def get_queryset(self):
        return super(CosinnusConferenceManager, self).get_queryset().filter(type=CosinnusGroup.TYPE_CONFERENCE)

    get_query_set = get_queryset


@python_2_unicode_compatible
class CosinnusProject(get_cosinnus_group_model()):
    
    class Meta(object):
        """ For some reason, the Meta isn't inherited automatically from CosinnusGroup here """
        proxy = True
        app_label = 'cosinnus'
        ordering = ('name',)
        verbose_name = _('Cosinnus project')
        verbose_name_plural = _('Cosinnus projects')
    
    GROUP_MODEL_TYPE = CosinnusGroup.TYPE_PROJECT
    MEMBERSHIP_MODE_CHOICES = [CosinnusGroup.MEMBERSHIP_MODE_CHOICES[mode] for mode in settings.COSINNUS_GROUP_MEMBERSHIP_MODE_CHOICES[GROUP_MODEL_TYPE]]
    
    objects = CosinnusProjectManager()
    
    def save(self, allow_type_change=False, *args, **kwargs):
        if not allow_type_change:
            self.type = CosinnusGroup.TYPE_PROJECT
        super(CosinnusProject, self).save(*args, **kwargs)
        
    def __str__(self):
        # FIXME: better caching for .portal.name
        return '%s (%s)' % (self.name, self.portal.name)
    
    @classmethod
    def get_trans(cls):
        """ Added this for IDEs and parsers to not mark the unknown `get_trans()` property everywhere the subtypes are 
            called using this directly. """
        return super(CosinnusProject, cls).get_trans()
        

@python_2_unicode_compatible
class CosinnusSociety(get_cosinnus_group_model()):
    
    class Meta(object):
        """ For some reason, the Meta isn't inherited automatically from CosinnusGroup here """
        proxy = True        
        app_label = 'cosinnus'
        ordering = ('name',)
        verbose_name = _('Cosinnus group')
        verbose_name_plural = _('Cosinnus groups')
    
    GROUP_MODEL_TYPE = CosinnusGroup.TYPE_SOCIETY
    MEMBERSHIP_MODE_CHOICES = [CosinnusGroup.MEMBERSHIP_MODE_CHOICES[mode] for mode in settings.COSINNUS_GROUP_MEMBERSHIP_MODE_CHOICES[GROUP_MODEL_TYPE]]
    
    objects = CosinnusSocietyManager()
    
    def save(self, allow_type_change=False, *args, **kwargs):
        if not allow_type_change:
            self.type = CosinnusGroup.TYPE_SOCIETY
        super(CosinnusSociety, self).save(*args, **kwargs)
    
    def __str__(self):
        # FIXME: better caching for .portal.name
        return '%s (%s)' % (self.name, self.portal.name)

    @classmethod
    def get_trans(cls):
        """ Added this for IDEs and parsers to not mark the unknown `get_trans()` property everywhere the subtypes are 
            called using this directly. """
        return super(CosinnusSociety, cls).get_trans()
    

class CosinnusConference(get_cosinnus_group_model()):
    
    class Meta(object):
        """ For some reason, the Meta isn't inherited automatically from CosinnusGroup here """
        proxy = True        
        app_label = 'cosinnus'
        ordering = ('name',)
        verbose_name = get_group_trans_by_type(CosinnusGroup.TYPE_CONFERENCE).VERBOSE_NAME
        verbose_name_plural = get_group_trans_by_type(CosinnusGroup.TYPE_CONFERENCE).VERBOSE_NAME_PLURAL
    
    GROUP_MODEL_TYPE = CosinnusGroup.TYPE_CONFERENCE
    MEMBERSHIP_MODE_CHOICES = [CosinnusGroup.MEMBERSHIP_MODE_CHOICES[mode] for mode in settings.COSINNUS_GROUP_MEMBERSHIP_MODE_CHOICES[GROUP_MODEL_TYPE]]
    
    objects = CosinnusConferenceManager()
    
    def save(self, allow_type_change=False, *args, **kwargs):
        """ Conferences do their check for whether or not they should be premium after saving """
        if not allow_type_change:
            self.type = CosinnusGroup.TYPE_CONFERENCE
        super(CosinnusConference, self).save(*args, **kwargs)
        from cosinnus_conference.utils import update_conference_premium_status
        update_conference_premium_status(conferences=[self])

    def __str__(self):
        # FIXME: better caching for .portal.name
        return '%s (%s)' % (self.name, self.portal.name)

    @classmethod
    def get_trans(cls):
        """ Added this for IDEs and parsers to not mark the unknown `get_trans()` property everywhere the subtypes are 
            called using this directly. """
        return super(CosinnusConference, cls).get_trans()
    

    
CosinnusGroup = get_cosinnus_group_model()


def ensure_group_type(group):
    """ If the given group is a CosinnusGroup model instance,
        returns it as either a CosinnusProject or CosinnusSociety,
        depending on group type """
    if group.__class__ == get_cosinnus_group_model():
        klass_map = {
            group.TYPE_PROJECT: CosinnusProject,
            group.TYPE_SOCIETY: CosinnusSociety,
            group.TYPE_CONFERENCE: CosinnusConference,
        }
        klass = klass_map.get(group.type)
        group = get_object_or_None(klass, id=group.id)
    return group
