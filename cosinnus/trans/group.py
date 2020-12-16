# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings
from cosinnus.utils.functions import resolve_class


class CosinnusProjectTransBase(object):
    """ A class containing all type-specific translation strings for the abstract typed
        CosinnusBaseGroup variations.
        Can be drop-in replaced per-portal with the setting `COSINNUS_GROUP_TRANS_TYPED_CLASSES_DROPINS`
        to vary the names of i.e. "Conferences" to "Expos".
        Always inherit at least the base class `CosinnusProjectTransBase` to make sure no 
        class members are missing! """
    
    ICON = 'fa-group'
    
    VERBOSE_NAME = _('Project')
    VERBOSE_NAME_PLURAL = _('Projects')
    
    MENU_LABEL = _('Project Menu')
    DASHBOARD_LABEL = _('Project Dashboard')
    CREATE = _('Create Project')
    CREATE_NEW = _('Create new Project')
    CREATE_DESCRIPTION = _('Organize your projects or initiatives efficiently with your fellow campaigners. All important tools for collaborating in one place: News, Pads, Events, Todos, and more.')
    EDIT = _('Edit Project')
    ACTIVATE = _('Activate Project')
    REACTIVATE = _('Re-activate Project')
    DEACTIVATE = _('Deactivate Project')
    CONVERT_ITEMS_TO = _('Convert selected items to Projects')
    
    FORMFIELD_NAME = _('Project name')
    
    MESSAGE_ONLY_ADMINS_MAY_CREATE = _('Sorry, only portal administrators can create Projects! You can write a message to one of the administrators to create a Project for you. Below you can find a listing of all administrators.')
    MESSAGE_ONLY_ADMINS_MAY_DEACTIVATE = _('Sorry, only portal administrators can deactivate Projects! You can write a message to one of the administrators to deactivate it for you. Below you can find a listing of all administrators.')
    

class CosinnusSocietyTransBase(CosinnusProjectTransBase):
    """ A class containing all type-specific translation strings for the abstract typed
        CosinnusBaseGroup variations.
        Can be drop-in replaced per-portal with the setting `COSINNUS_GROUP_TRANS_TYPED_CLASSES_DROPINS`
        to vary the names of i.e. "Conferences" to "Expos".
    """
    
    ICON = 'fa-sitemap'
    
    VERBOSE_NAME = _('Group')
    VERBOSE_NAME_PLURAL = _('Groups')
    
    MENU_LABEL = _('Group Menu')
    DASHBOARD_LABEL = _('Group Dashboard')
    CREATE = _('Create Group')
    CREATE_NEW = _('Create new Group')
    CREATE_DESCRIPTION = _('Groups help improve communication and collaboration in large networks or organisations. Within a Group you can bring together several smaller projects or workgroups.')
    EDIT = _('Edit Group')
    ACTIVATE = _('Activate Group')
    REACTIVATE = _('Re-activate Group')
    DEACTIVATE = _('Deactivate Group')
    CONVERT_ITEMS_TO = _('Convert selected items to Groups')
    
    FORMFIELD_NAME = _('Group name')
    
    MESSAGE_ONLY_ADMINS_MAY_CREATE = _('Sorry, only portal administrators can create Groups! You can write a message to one of the administrators to create a Group for you. Below you can find a listing of all administrators.')
    MESSAGE_ONLY_ADMINS_MAY_DEACTIVATE = _('Sorry, only portal administrators can deactivate Groups! You can write a message to one of the administrators to deactivate it for you. Below you can find a listing of all administrators.')
    
    
class CosinnusConferenceTransBase(CosinnusProjectTransBase):
    """ A class containing all type-specific translation strings for the abstract typed
        CosinnusBaseGroup variations.
        Can be drop-in replaced per-portal with the setting `COSINNUS_GROUP_TRANS_TYPED_CLASSES_DROPINS`
        to vary the names of i.e. "Conferences" to "Expos".
    """
    
    ICON = 'fa-television'
    
    VERBOSE_NAME = _('Conference')
    VERBOSE_NAME_PLURAL = _('Conferences')
    
    MENU_LABEL = _('Conference Menu')
    DASHBOARD_LABEL = _('Conference Dashboard')
    CREATE = _('Create Conference')
    CREATE_NEW = _('Create new Conference')
    CREATE_DESCRIPTION = _('Conferences let you set up and host workshops and events over multiple days, complete with video messaging, stage stream integration, breakout rooms and lobby chats.')
    EDIT = _('Edit Conference')
    ACTIVATE = _('Activate Conference')
    REACTIVATE = _('Re-activate Conference')
    DEACTIVATE = _('Deactivate Conference')
    CONVERT_ITEMS_TO = _('Convert selected items to Conferences')
    
    FORMFIELD_NAME = _('Conference name')
    
    MESSAGE_ONLY_ADMINS_MAY_CREATE = _('Sorry, only portal administrators can create Conferences! You can write a message to one of the administrators to create a Conference for you. Below you can find a listing of all administrators.')
    MESSAGE_ONLY_ADMINS_MAY_DEACTIVATE = _('Sorry, only portal administrators can deactivate Conferences! You can write a message to one of the administrators to deactivate it for you. Below you can find a listing of all administrators.')
    

# allow dropin of trans classes
CosinnusProjectTrans = CosinnusProjectTransBase
if getattr(settings, 'COSINNUS_GROUP_TRANS_TYPED_CLASSES_DROPINS', {}).get(0, None):
    CosinnusProjectTrans = resolve_class(settings.COSINNUS_GROUP_TRANS_TYPED_CLASSES_DROPINS[0])
    
CosinnusSocietyTrans = CosinnusSocietyTransBase
if getattr(settings, 'COSINNUS_GROUP_TRANS_TYPED_CLASSES_DROPINS', {}).get(1, None):
    CosinnusSocietyTrans = resolve_class(settings.COSINNUS_GROUP_TRANS_TYPED_CLASSES_DROPINS[1])
    
CosinnusConferenceTrans = CosinnusConferenceTransBase
if getattr(settings, 'COSINNUS_GROUP_TRANS_TYPED_CLASSES_DROPINS', {}).get(2, None):
    CosinnusConferenceTrans = resolve_class(settings.COSINNUS_GROUP_TRANS_TYPED_CLASSES_DROPINS[2])

GROUP_TRANS_MAP = {
    0: CosinnusProjectTrans,
    1: CosinnusSocietyTrans,
    2: CosinnusConferenceTrans,
}

def get_group_trans_by_type(group_type):
    return GROUP_TRANS_MAP.get(group_type, CosinnusProjectTrans)

