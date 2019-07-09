# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
from django.db.models import Q

from cosinnus.models.group import CosinnusPortal, CosinnusPortalMembership,\
    MEMBERSHIP_ADMIN
from cosinnus.models.tagged import BaseTaggableObjectModel, BaseTagObject,\
    BaseHierarchicalTaggableObjectModel
from cosinnus.models.profile import BaseUserProfile, GlobalBlacklistedEmail,\
    GlobalUserNotificationSetting
from uuid import uuid1
from django.conf import settings
from cosinnus.utils.group import get_cosinnus_group_model,\
    get_default_user_group_ids
from cosinnus.models.idea import CosinnusIdea
from annoying.functions import get_object_or_None


def check_ug_admin(user, group):
    """Returns ``True`` if the given user is admin of the given group.
    ``False`` otherwise.

    :param User user: The user object to check
    :param Group group: The group object to check
    :returns: True if the user is a member of the given group.
    """
    return group.is_admin(user)


def check_ug_membership(user, group):
    """Returns ``True`` if the given user is member or admin of the given
    group. ``False`` otherwise.

    :param User user: The user object to check
    :param Group group: The group object to check
    :returns: True if the user is a member of the group.
    """
    return group.is_member(user)


def check_ug_pending(user, group):
    """Returns ``True`` if the given user is has requested to be a member of this
    group. ``False`` otherwise.

    :param User user: The user object to check
    :param Group group: The group object to check
    :returns: True if the user is a member of the group.
    """
    return group.is_pending(user)


def check_ug_invited_pending(user, group):
    """Returns ``True`` if the given user has been invited to join
    group. ``False`` otherwise.

    :param User user: The user object to check
    :param Group group: The group object to check
    :returns: True if the user is a member of the group.
    """
    return group.is_invited_pending(user)


def check_object_read_access(obj, user):
    """ Checks read permissions for a CosinnusGroup or BaseTaggableObject or any object with a creator attribute.
        Returns ``True`` if the user is either admin, staff member, group admin, group member,
            or the group is public.
    """
    # check what kind of object was supplied (CosinnusGroup or BaseTaggableObject)
    if type(obj) is get_cosinnus_group_model() or issubclass(obj.__class__, get_cosinnus_group_model()):
        group = obj
        is_member = check_ug_membership(user, group)
        is_admin = check_ug_admin(user, group) 
        return (group.public and user.is_authenticated) or check_user_superuser(user) or is_member or is_admin
    
    elif issubclass(obj.__class__, BaseTaggableObjectModel):
        group = obj.group
        is_member = check_ug_membership(user, group)
        is_admin = check_ug_admin(user, group)
        # items are readable only if their visibility tag is public, or it is set to group and a group member
        # is accessing the item, or the item's creator is accessing it
        if obj.media_tag:
            obj_is_visible = obj.creator == user or \
                    obj.media_tag.visibility == BaseTagObject.VISIBILITY_ALL or \
                    (obj.media_tag.visibility == BaseTagObject.VISIBILITY_GROUP and (is_member or is_admin))
        elif issubclass(obj.__class__, BaseHierarchicalTaggableObjectModel) and obj.is_container:
            # folders do not have a media tag and inherit visibility from the group
            obj_is_visible = group.public or is_member or is_admin
        else:
            # catch error cases where no media_tag was created. that case should break, but not here.
            obj_is_visible = is_member or is_admin
        return check_user_superuser(user) or obj_is_visible or obj.grant_extra_read_permissions(user)
    elif type(obj) is CosinnusIdea:
        # ideas are only either public or visible by any logged in user, no private setting
        return obj.public or user.is_authenticated
    elif issubclass(obj.__class__, BaseUserProfile):
        return check_user_can_see_user(user, obj.user)
    else:
        met_proper_object_conditions = False
        extra_conditions = False
        if hasattr(obj, 'grant_extra_read_permissions'):
            extra_conditions = extra_conditions or obj.grant_extra_read_permissions(user)
            met_proper_object_conditions = True
        if hasattr(obj, 'creator'):
            extra_conditions = extra_conditions or (obj.creator == user or check_user_superuser(user))
            met_proper_object_conditions = True
        
        if not met_proper_object_conditions:
            raise Exception("cosinnus.core.permissions: You must either supply a CosinnusGroup " +\
            "or a BaseTaggableObject or an object with a ``creator`` property " +\
            "or an object with a ``grant_extra_read_permissions(self, user)`` function " +\
            "to check_object_read_access(). The supplied object " +\
            "type was: %s" % (str(obj.__class__) if obj else "None"))
        else:
            return extra_conditions

def check_object_write_access(obj, user, fields=None):
    """ Checks write permissions for either a CosinnusGroup and BaseTaggableObject or any object with a creator attribute.
        For CosinnusGroups, check if the user can edit/update/delete the group iself:
            returns ``True`` if the user is either admin, staff member or group admin
        For BaseTaggableObjects, check if the user can edit/update/delete the item iself:
            returns ``True`` if the user is either admin, staff member, object owner or group admin 
                of the group the item belongs to
        For Objects with a creator attribute, check if the user is the creator of that object or he is staff or admin.
        
        :param fields: Optional list of fields that are requested to be changed. This will be passed on to `
            ``obj.grant_extra_write_permissions()`` so that objects can make fine-grained decisions whether to allow
            write access to only select fields.
        
    """
    # check what kind of object was supplied (CosinnusGroup or BaseTaggableObject)
    if type(obj) is get_cosinnus_group_model() or issubclass(obj.__class__, get_cosinnus_group_model()):
        is_admin = check_ug_admin(user, obj)
        return is_admin or check_user_superuser(user)
    elif issubclass(obj.__class__, BaseTaggableObjectModel):
        # editing/deleting an object, check if we are owner or staff member or group admin or site admin
        is_admin = check_ug_admin(user, obj.group) if obj.group else False
        if obj.media_tag:
            is_private = obj.media_tag.visibility == BaseTagObject.VISIBILITY_USER
        else:
            # catch error cases where no media_tag was created. that case should break, but not here.
            is_private = False
        # folders can be edited by group members (except root folder)
        folder_for_group_member = issubclass(obj.__class__, BaseHierarchicalTaggableObjectModel) and \
                obj.is_container and not obj.path == '/' and check_ug_membership(user, obj.group)
            
        return check_user_superuser(user) or obj.creator == user or (is_admin and not is_private) \
            or obj.grant_extra_write_permissions(user, fields=fields) or folder_for_group_member
    elif issubclass(obj.__class__, BaseUserProfile):
        return obj.user == user or check_user_superuser(user)
    elif hasattr(obj, 'creator'):
        return obj.creator == user or check_user_superuser(user)
    elif hasattr(obj, 'grant_extra_write_permissions'):
        return obj.grant_extra_write_permissions(user, fields=fields) or check_user_superuser(user)
    
    raise Exception("cosinnus.core.permissions: You must either supply a CosinnusGroup " +\
            "or a BaseTaggableObject or an object with a ``creator`` property  " +\
            "or an object with a ``grant_extra_write_permissions(self, user)`` function " +\
            "to check_object_read_access(). The supplied object " +\
            "type was: %s" % (str(obj.__class__) if obj else "None"))

def check_group_create_objects_access(group, user):
    """ Checks permissions of a user to create objects in a CosinnusGroup.
            returns ``True`` if the user is either admin, staff member or group member
    """
    #  check if we can create objects in the group
    is_member = check_ug_membership(user, group)
    is_admin = check_ug_admin(user, group)
    return is_member or is_admin or check_user_superuser(user)

def check_object_likefollow_access(obj, user):
    """ Checks permissions of a user to like/follow an object.
        This permission may behave differently depending on the object model.
    """
    # liking this object must be enabled and user logged in
    if not (getattr(obj, 'IS_LIKEABLE_OBJECT', False) or user.is_authenticated):
        return False
    # groups can always be followed, and all other visible objects
    is_group = type(obj) is get_cosinnus_group_model() or issubclass(obj.__class__, get_cosinnus_group_model())
    return is_group or check_object_read_access(obj, user)

def check_user_can_see_user(user, target_user):
    """ Checks if ``user`` is in any relation with ``target_user`` so that he can see them and 
        their profile, and can send him messages, etc. 
        This depends on the privacy settings of ``target_user`` and on whether they are members 
        of a same group/project. """
    visibility = target_user.cosinnus_profile.media_tag.visibility
    
    if visibility == BaseTagObject.VISIBILITY_ALL:
        return True
    if visibility == BaseTagObject.VISIBILITY_GROUP and user.is_authenticated:
        return True
    if check_user_superuser(user):
        return True
    if user == target_user:
        return True
    
    # in any case, group members of the same project/group can always see each other
    # but filter the default groups for this!
    exclude_pks = get_default_user_group_ids()
    user_groups = [ug_pk for ug_pk in get_cosinnus_group_model().objects.get_for_user_pks(user) if not ug_pk in exclude_pks]
    target_user_groups = [tug_pk for tug_pk in get_cosinnus_group_model().objects.get_for_user_pks(target_user) if not tug_pk in exclude_pks]
    if any([(user_group_pk in target_user_groups) for user_group_pk in user_groups]):
        return True
    return False

def check_user_superuser(user, portal=None):
    """ Main function to determine whether a user has superuser rights to access and change almost
            any view and object on the site.
        For this it checks permissions if a user is a portal admin or a superuser
            returns ``True`` if the user is a superuser or portal admin
    """
    return user.is_superuser or check_user_portal_admin(user, portal)


def check_user_portal_admin(user, portal=None):
    """ Checks permissions if a user is a portal admin in the given or current portal.
            returns ``True`` if the user is a portal admin
    """
    portal = portal or CosinnusPortal.get_current()
    return user.id in portal.admins


def check_user_portal_moderator(user, portal=None):
    """ Checks if a user is a portal moderator (must also be portal admin) in the given or current portal.
            returns ``True`` if the user is a portal moderator
    """
    portal = portal or CosinnusPortal.get_current()
    # TODO: this is currently not cached since it is queried very seldomly 
    membership = get_object_or_None(CosinnusPortalMembership, status=MEMBERSHIP_ADMIN, group=portal, user=user)
    return bool(membership and membership.is_moderator)


def check_user_integrated_portal_member(user):
    """ Returns ``True`` if the user is a member, admin, or pending in an integrated Portal """
    portal_memberships = user.cosinnus_portal_memberships.all().values_list('group__id', flat=True)
    return any([portal_id in settings.COSINNUS_INTEGRATED_PORTAL_IDS for portal_id in portal_memberships])


def check_user_can_receive_emails(user):
    """ Checks if a user can receive emails *at all*, ignoring any frequency settings.
        This checks the global notification setting for authenticated users,
        and the email blacklist for anonymous users. """
    if not user.is_authenticated:
        return not GlobalBlacklistedEmail.is_email_blacklisted(user.email)
    else:
        return GlobalUserNotificationSetting.objects.get_for_user(user) > GlobalUserNotificationSetting.SETTING_NEVER


def filter_tagged_object_queryset_for_user(qs, user):
    """ A queryset filter to filter for TaggableObjects that respects the visibility tag of the object,
        checking group membership of the user and creator information of the object.
        This is used to filter all list views and queryset gets for BaseTaggableObjects.
        
        Since we are filtering on a many-to-many field (persons), we need to make the QS distinct.
        
        @return: the filtered queryset
         """
    # always exclude all items from inactive groups
    qs = qs.filter(group__is_active=True)
    
    # admins may see everything
    if check_user_superuser(user):
        return qs
    
    q = Q(media_tag__isnull=True) # get all objects that don't have a media_tag (folders for example)
    q |= Q(media_tag__visibility=BaseTagObject.VISIBILITY_ALL)  # All public tagged objects
    if user.is_authenticated:
        gids = get_cosinnus_group_model().objects.get_for_user_pks(user)
        q |= Q(  # all tagged objects in groups the user is a member of
            media_tag__visibility=BaseTagObject.VISIBILITY_GROUP,
            group_id__in=gids
        )
        q |= Q(  # all tagged objects the user is explicitly a linked to
            media_tag__visibility=BaseTagObject.VISIBILITY_USER,
            media_tag__persons__id__exact=user.id
        )
        q |= Q( # all tagged objects of the user himself
            media_tag__visibility=BaseTagObject.VISIBILITY_USER,
            creator__id=user.id
        )
    return qs.filter(q).distinct()


def get_user_token(user, token_name):
    """ Retrieves or generates a permanent token for a user and
        a given token identifier. Use these tokens only for one
        specific purpose each! """
        
    token = user.cosinnus_profile.settings.get('token:%s' % token_name, None)
    if not token:
        token = str(uuid1().int)
        user.cosinnus_profile.settings['token:%s' % token_name] = token
        user.cosinnus_profile.save()
    return token
