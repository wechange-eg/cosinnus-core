# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from cosinnus.models.group import CosinnusGroup
from cosinnus.models.tagged import BaseTaggableObjectModel, BaseTagObject


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
    """Returns ``True`` if the given user is member or admin of the given
    group. ``False`` otherwise.

    :param User user: The user object to check
    :param Group group: The group object to check
    :returns: True if the user is a member of the group.
    """
    return group.is_pending(user)



def check_object_read_access(obj, user):
    """ Checks read permissions for a CosinnusGroup or BaseTaggableObject.
        Returns ``True`` if the user is either admin, staff member, group admin, group member,
            or the group is public.
    """
    # check what kind of object was supplied (CosinnusGroup or BaseTaggableObject)
    if type(obj) is CosinnusGroup:
        group = obj
        is_member = check_ug_membership(user, group)
        is_admin = check_ug_admin(user, group)
        return group.public or user.is_superuser or user.is_staff or is_member or is_admin
    
    elif issubclass(obj.__class__, BaseTaggableObjectModel):
        group = obj.group
        is_member = check_ug_membership(user, group)
        is_admin = check_ug_admin(user, group)
        # items are readable only if their visibility tag is public, or it is set to group and a group member
        # is accessing the item, or the item's creator is accessing it
        obj_is_visible = obj.creator == user or \
                obj.media_tag.visibility == BaseTagObject.VISIBILITY_ALL or \
                (obj.media_tag.visibility == BaseTagObject.VISIBILITY_GROUP and (is_member or is_admin))
        
        return user.is_superuser or user.is_staff or obj_is_visible
    
    else:
        raise Exception("cosinnus.core.permissions: You must either supply a CosinnusGroup \
                or a BaseTaggableObject to check_object_read_access(). The supplied object \
                type was: %s" % (str(obj.__class__) if obj else "None"))
    


def check_object_write_access(obj, user):
    """ Checks write permissions for either a CosinnusGroup and BaseTaggableObject.
        For CosinnusGroups, check if the user can edit/update/delete the group iself:
            returns ``True`` if the user is either admin, staff member or group admin
        For BaseTaggableObjects, check if the user can edit/update/delete the item iself:
            returns ``True`` if the user is either admin, staff member, object owner or group admin 
                of the group the item belongs to
        
    """
    # check what kind of object was supplied (CosinnusGroup or BaseTaggableObject)
    if type(obj) is CosinnusGroup:
        is_admin = check_ug_admin(user, obj)
        return is_admin or user.is_superuser or user.is_staff
    elif issubclass(obj.__class__, BaseTaggableObjectModel):
        # editing/deleting an object, check if we are owner or staff member or group admin or site admin
        is_admin = check_ug_admin(user, obj.group)
        is_private = obj.media_tag.visibility == BaseTagObject.VISIBILITY_USER
        return user.is_superuser or user.is_staff or obj.creator == user or (is_admin and not is_private)
    
    raise Exception("cosinnus.core.permissions: You must either supply a CosinnusGroup \
            or a BaseTaggableObject to check_object_write_access(). The supplied object \
            type was: %s" % (str(obj.__class__) if obj else "None"))

def check_group_create_objects_access(group, user):
    """ Checks permissions of a user to create objects in a CosinnusGroup.
            returns ``True`` if the user is either admin, staff member or group member
    """
    #  check if we can create objects in the group
    is_member = check_ug_membership(user, group)
    is_admin = check_ug_admin(user, group)
    return is_member or is_admin or user.is_superuser or user.is_staff