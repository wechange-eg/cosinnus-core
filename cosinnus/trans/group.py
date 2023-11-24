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
    ALL_LIST = _('All Projects')
    MY_LIST = _('My Projects')
    MY_LIST_EMPTY = _('You are not currently in any Projects')
    MY_UPCOMING_LIST = _('My upcoming Projects')
    
    MENU_LABEL = _('Project Menu')
    DASHBOARD_LABEL = _('Project Dashboard')
    DASHBOARD_LABEL_ON = _('in the Project Dashboard')
    BROWSE_ALL = _('Browse all Projects')
    CREATE = _('Create Project')
    CREATE_NEW = _('Create new Project')
    CREATE_DESCRIPTION = _('Organize your projects or initiatives efficiently with your fellow campaigners. All important tools for collaborating in one place: News, Pads, Events, Todos, and more.')
    EDIT = _('Edit Project')
    ACTIVATE = _('Activate Project')
    REACTIVATE = _('Re-activate Project')
    DEACTIVATE = _('Deactivate Project')
    DEACTIVATE_WARNING = _('You are about to deactivate this project!')
    REACTIVATE_EXPLANATION = _('You are about to re-activate this project. It and all of its content will be visible on the website again.')
    DEACTIVATE_EXPLANATION = _('You are about to deactivate this project. When your project is deactivated, it is no longer accessible and will be removed from the website. However, your data will still be retained.\n\n Please contact the administrators of this portal if you would like to irrevocably delete all of the content. Until then the project can be reactivated by your and any other project administrator.')
    CONVERT_ITEMS_TO = _('Convert selected items to Projects')
    CONTACT_PERSON = _('Project administrator')
    CONTACT_ROOM_TOPIC = _('Request about your project "%(group_name)s"')
    CONTACT_ROOM_GREETING_MESSAGE = _('You are now in a private channel with the admins of this project.')
    
    FORMFIELD_NAME = _('Project name')
    FORMFIELD_NAME_PLACEHOLDER = _('Enter a name for the project.')
    FORMFIELD_DESCRIPTION_LEGEND = _('Describe the project in a few sentences.')
    FORMFIELD_LOCATION_LABEL = _('Where is the project active?')
    FORMFIELD_VISIBILITY_CHOICE_MEMBERS_ONLY = _('Project members only')
    FORMFIELD_MEMBERSHIP_MODE_TYPE_0_LEGEND = _("Users may join by submitting a membership request that can be accepted or declined by any of the project's administrators.")
    FORMFIELD_ATTACH_OBJECTS_HINT = _('Type the names of files, events or pads from this project to attach...')
    
    CALL_TO_JOIN = _('Collaborate!')
    CALL_TO_REGISTER_AND_JOIN = _('Join now and collaborate!')
    INVITED_TO_JOIN = _('You have been invited to collaborate!')
    GUEST_BROWSE_ONLY = _('You can access and browse the project that invited you')
    
    MESSAGE_ONLY_ADMINS_MAY_CREATE = _('Sorry, only portal administrators can create Projects! You can write a message to one of the administrators to create a Project for you. Below you can find a listing of all administrators.')
    MESSAGE_ONLY_ADMINS_MAY_DEACTIVATE = _('Sorry, only portal administrators can deactivate Projects! You can write a message to one of the administrators to deactivate it for you. Below you can find a listing of all administrators.')
    MESSAGE_MEMBERS_ONLY = _('Only project members can see the content you requested. Apply to become a member now!')
    
    MESSAGE_RECORDINGS_ONLY_FOR_PREMIUM = _('Note: New recordings can only be made if you have booked premium features for this project.')


class CosinnusSocietyTransBase(CosinnusProjectTransBase):
    """ A class containing all type-specific translation strings for the abstract typed
        CosinnusBaseGroup variations.
        Can be drop-in replaced per-portal with the setting `COSINNUS_GROUP_TRANS_TYPED_CLASSES_DROPINS`
        to vary the names of i.e. "Conferences" to "Expos".
    """
    
    ICON = 'fa-sitemap'
    
    VERBOSE_NAME = _('Group')
    VERBOSE_NAME_PLURAL = _('Groups')
    ALL_LIST = _('All Groups')
    MY_LIST = _('My Groups')
    MY_LIST_EMPTY = _('You are not currently in any Groups')
    MY_UPCOMING_LIST = _('My upcoming Groups')
    
    MENU_LABEL = _('Group Menu')
    DASHBOARD_LABEL = _('Group Dashboard')
    DASHBOARD_LABEL_ON = _('in the Group Dashboard')

    BROWSE_ALL = _('Browse all Groups')
    CREATE = _('Create Group')
    CREATE_NEW = _('Create new Group')
    CREATE_DESCRIPTION = _('Groups help improve communication and collaboration in large networks or organizations. Within a Group you can bring together several smaller projects or workgroups.')
    EDIT = _('Edit Group')
    ACTIVATE = _('Activate Group')
    REACTIVATE = _('Re-activate Group')
    DEACTIVATE = _('Deactivate Group')
    DEACTIVATE_WARNING = _('You are about to deactivate this group!')
    REACTIVATE_EXPLANATION = _('You are about to re-activate this group. It and all of its content will be visible on the website again.')
    DEACTIVATE_EXPLANATION = _('You are about to deactivate this group. When your group is deactivated, it is no longer accessible and will be removed from the website. However, your data will still be retained.\n\n Please contact the administrators of this portal if you would like to irrevocably delete all of the content. Until then the group can be reactivated by your and any other group administrator.')
    CONVERT_ITEMS_TO = _('Convert selected items to Groups')
    CONTACT_PERSON = _('Group administrator')
    CONTACT_ROOM_TOPIC = _('Request about your group "%(group_name)s"')
    CONTACT_ROOM_GREETING_MESSAGE = _('You are now in a private channel with the admins of this group.')
    
    FORMFIELD_NAME = _('Group name')
    FORMFIELD_NAME_PLACEHOLDER = _('Enter a name for the group.')
    FORMFIELD_DESCRIPTION_LEGEND = _('Describe the group in a few sentences.')
    FORMFIELD_LOCATION_LABEL = _('Where is the group active?')
    FORMFIELD_VISIBILITY_CHOICE_MEMBERS_ONLY = _('Group members only')
    FORMFIELD_MEMBERSHIP_MODE_TYPE_0_LEGEND = _("Users may join by submitting a membership request that can be accepted or declined by any of the groups's administrators.")
    FORMFIELD_ATTACH_OBJECTS_HINT = _('Type the names of files, events or pads from this group to attach...')
    
    CALL_TO_JOIN = _('Collaborate!')
    CALL_TO_REGISTER_AND_JOIN = _('Join now and collaborate!')
    INVITED_TO_JOIN = _('You have been invited to collaborate!')
    GUEST_BROWSE_ONLY = _('You can access and browse the group that invited you')
    
    MESSAGE_ONLY_ADMINS_MAY_CREATE = _('Sorry, only portal administrators can create Groups! You can write a message to one of the administrators to create a Group for you. Below you can find a listing of all administrators.')
    MESSAGE_ONLY_ADMINS_MAY_DEACTIVATE = _('Sorry, only portal administrators can deactivate Groups! You can write a message to one of the administrators to deactivate it for you. Below you can find a listing of all administrators.')
    MESSAGE_MEMBERS_ONLY = _('Only group members can see the content you requested. Apply to become a member now!')
    
    MESSAGE_RECORDINGS_ONLY_FOR_PREMIUM = _('Note: New recordings can only be made if you have booked premium features for this group.')
    

class CosinnusConferenceTransBase(CosinnusProjectTransBase):
    """ A class containing all type-specific translation strings for the abstract typed
        CosinnusBaseGroup variations.
        Can be drop-in replaced per-portal with the setting `COSINNUS_GROUP_TRANS_TYPED_CLASSES_DROPINS`
        to vary the names of i.e. "Conferences" to "Expos".
    """
    
    ICON = 'fa-television'
    
    VERBOSE_NAME = _('Conference')
    VERBOSE_NAME_PLURAL = _('Conferences')
    ALL_LIST = _('All Conferences')
    MY_LIST = _('My Conferences')
    MY_LIST_EMPTY = _('You are not currently attending any Conferences')
    MY_UPCOMING_LIST = _('My upcoming Conferences')
    
    MENU_LABEL = _('Conference Menu')
    DASHBOARD_LABEL = VERBOSE_NAME
    DASHBOARD_LABEL_ON = VERBOSE_NAME
    BROWSE_ALL = _('Browse all Conferences')
    CREATE = _('Create Conference')
    CREATE_NEW = _('Create new Conference')
    CREATE_DESCRIPTION = _('Conferences let you set up and host workshops and events over multiple days, complete with video messaging, stage stream integration, breakout rooms and lobby chats.')
    EDIT = _('Edit Conference')
    ACTIVATE = _('Activate Conference')
    REACTIVATE = _('Re-activate Conference')
    DEACTIVATE = _('Deactivate Conference')
    DEACTIVATE_WARNING = _('You are about to deactivate this conference!')
    REACTIVATE_EXPLANATION = _('You are about to re-activate this conference. It and all of its content will be visible on the website again.')
    DEACTIVATE_EXPLANATION = _('You are about to deactivate this conference. When your conference is deactivated, it is no longer accessible and will be removed from the website. However, your data will still be retained.\n\n Please contact the administrators of this portal if you would like to irrevocably delete all of the content. Until then the conference can be reactivated by your and any other conference organizer.')
    CONVERT_ITEMS_TO = _('Convert selected items to Conferences')
    CONTACT_PERSON = _('Conference contact person')
    CONTACT_ROOM_TOPIC = _('Request about your conference "%(group_name)s"')
    CONTACT_ROOM_GREETING_MESSAGE = _('You are now in a private channel with the organizers of this conference.')
    
    FORMFIELD_NAME = _('Conference name')
    FORMFIELD_NAME_PLACEHOLDER = _('Enter a name for the conference.')
    FORMFIELD_DESCRIPTION_LEGEND = _('Describe the conference in a few sentences.')
    FORMFIELD_LOCATION_LABEL = _('Where is the conference active?')
    FORMFIELD_VISIBILITY_CHOICE_MEMBERS_ONLY = _('Conference members only')
    FORMFIELD_MEMBERSHIP_MODE_TYPE_0_LEGEND = _("Users may join by submitting a membership request that can be accepted or declined by any of the conference's organizers.")
    FORMFIELD_ATTACH_OBJECTS_HINT = _('Type the names of files, events or pads from this conference to attach...')
    
    CALL_TO_JOIN = _('Participate!')
    CALL_TO_REGISTER_AND_JOIN = _('Join now and participate!')
    INVITED_TO_JOIN = _('You have been invited to participate!')
    GUEST_BROWSE_ONLY = _('You can access and participate in the conference that invited you')
    
    MESSAGE_ONLY_ADMINS_MAY_CREATE = _('Sorry, only portal administrators can create Conferences! You can write a message to one of the administrators to create a Conference for you. Below you can find a listing of all administrators.')
    MESSAGE_ONLY_ADMINS_MAY_DEACTIVATE = _('Sorry, only portal administrators can deactivate Conferences! You can write a message to one of the administrators to deactivate it for you. Below you can find a listing of all administrators.')
    MESSAGE_MEMBERS_ONLY = _('Only conference members can see the content you requested. Apply to become a member now!')
    
    MESSAGE_RECORDINGS_ONLY_FOR_PREMIUM = _('Note: New recordings can only be made if you have booked premium features for this conference.')
    
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

