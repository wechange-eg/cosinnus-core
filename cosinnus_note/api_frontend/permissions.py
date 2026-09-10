from rest_framework.permissions import BasePermission

from cosinnus.conf import settings
from cosinnus.utils.group import get_cosinnus_group_model


def check_user_can_post_to_forum(user):
    """Helper to check if a user can post to the forum group."""
    # check user is authenticated and verified
    if not user.is_authenticated or not user.is_account_verified:
        return False
    # check portal and group settings
    if (
        settings.COSINNUS_FORUM_DISABLED
        or settings.COSINNUS_POST_TO_FORUM_FROM_DASHBOARD_DISABLED
        or not settings.NEWW_FORUM_GROUP_SLUG
        or 'cosinnus_note' in settings.COSINNUS_DISABLED_COSINNUS_APPS
    ):
        return False
    # check forum group exists and has notes app active
    forum_group = get_cosinnus_group_model().objects.filter(slug=settings.NEWW_FORUM_GROUP_SLUG).first()
    if not forum_group or 'cosinnus_note' in forum_group.get_deactivated_apps():
        return False
    # check user is forum member
    if not forum_group.is_member(user):
        return False
    return True


class CosinnusNoteForumPostPermissions(BasePermission):
    """Permission class for Forum Post action."""

    def has_permission(self, request, view):
        return check_user_can_post_to_forum(request.user)
