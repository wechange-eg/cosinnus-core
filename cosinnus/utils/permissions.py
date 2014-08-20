# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models import Q

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
    """ Checks read permissions for a CosinnusGroup or BaseTaggableObject or any object with a creator attribute.
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
        if obj.media_tag:
            obj_is_visible = obj.creator == user or \
                    obj.media_tag.visibility == BaseTagObject.VISIBILITY_ALL or \
                    (obj.media_tag.visibility == BaseTagObject.VISIBILITY_GROUP and (is_member or is_admin))
        else:
            # catch error cases where no media_tag was created. that case should break, but not here.
            obj_is_visible = is_member or is_admin
        return user.is_superuser or user.is_staff or obj_is_visible
    elif hasattr(obj, 'creator'):
        return obj.creator == user or user.is_superuser or user.is_staff
    
    raise Exception("cosinnus.core.permissions: You must either supply a CosinnusGroup " +\
            "or a BaseTaggableObject or an object with a ``creator`` property to " +\
            "check_object_read_access(). The supplied object " +\
            "type was: %s" % (str(obj.__class__) if obj else "None"))
    

def check_object_write_access(obj, user):
    """ Checks write permissions for either a CosinnusGroup and BaseTaggableObject or any object with a creator attribute.
        For CosinnusGroups, check if the user can edit/update/delete the group iself:
            returns ``True`` if the user is either admin, staff member or group admin
        For BaseTaggableObjects, check if the user can edit/update/delete the item iself:
            returns ``True`` if the user is either admin, staff member, object owner or group admin 
                of the group the item belongs to
        For Objects with a creator attribute, check if the user is the creator of that object or he is staff or admin.
        
    """
    # check what kind of object was supplied (CosinnusGroup or BaseTaggableObject)
    if type(obj) is CosinnusGroup:
        is_admin = check_ug_admin(user, obj)
        return is_admin or user.is_superuser or user.is_staff
    elif issubclass(obj.__class__, BaseTaggableObjectModel):
        # editing/deleting an object, check if we are owner or staff member or group admin or site admin
        is_admin = check_ug_admin(user, obj.group) if obj.group else False
        if obj.media_tag:
            is_private = obj.media_tag.visibility == BaseTagObject.VISIBILITY_USER
        else:
            # catch error cases where no media_tag was created. that case should break, but not here.
            is_private = False
        return user.is_superuser or user.is_staff or obj.creator == user or (is_admin and not is_private)
    elif hasattr(obj, 'creator'):
        return obj.creator == user or user.is_superuser or user.is_staff
    
    raise Exception("cosinnus.core.permissions: You must either supply a CosinnusGroup " +\
            "or a BaseTaggableObject or an object with a ``creator`` property to " +\
            "check_object_read_access(). The supplied object " +\
            "type was: %s" % (str(obj.__class__) if obj else "None"))

def check_group_create_objects_access(group, user):
    """ Checks permissions of a user to create objects in a CosinnusGroup.
            returns ``True`` if the user is either admin, staff member or group member
    """
    #  check if we can create objects in the group
    is_member = check_ug_membership(user, group)
    is_admin = check_ug_admin(user, group)
    return is_member or is_admin or user.is_superuser or user.is_staff


def get_tagged_object_filter_for_user(user):
    """ A queryset filter to filter for TaggableObjects that respects the visibility tag of the object,
        checking group membership of the user and creator information of the object.
        This is used to filter all list views and queryset gets for BaseTaggableObjects. """
    q = Q(media_tag__isnull=True) # get all objects that don't have a media_tag (folders for example)
    q |= Q(media_tag__visibility=BaseTagObject.VISIBILITY_ALL)  # All public tagged objects
    if user.is_authenticated():
        gids = CosinnusGroup.objects.get_for_user_pks(user)
        q |= Q(  # all tagged objects in groups the user is a member of
            media_tag__visibility=BaseTagObject.VISIBILITY_GROUP,
            group_id__in=gids
        )
        q |= Q(  # all tagged objects the user is explicitly a linked to
            media_tag__visibility=BaseTagObject.VISIBILITY_USER,
            media_tag__persons__id=user.id
        )
        q |= Q( # all tagged objects of the user himself
            media_tag__visibility=BaseTagObject.VISIBILITY_USER,
            creator__id=user.id
        )
    return q
