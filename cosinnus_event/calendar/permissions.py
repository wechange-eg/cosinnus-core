from rest_framework.permissions import BasePermission

from cosinnus.utils.permissions import (
    check_group_create_objects_access,
    check_object_write_access,
)


class CalendarPublicEventPermissions(BasePermission):
    """Permissions for the calendar events viewset."""

    def has_permission(self, request, view):
        if view.action == 'list':
            # Listing of public events is allowed for everybody
            return True
        elif view.action == 'create':
            # Check create permission for user in the group
            return check_group_create_objects_access(view.group, request.user)
        elif view.action == 'attendance':
            # Attendance is allowed for logged-in users
            return request.user.is_authenticated
        # Return True, permissions for other operations are check per object in has_object_permission.
        return True

    def has_object_permission(self, request, view, obj):
        if view.action in ['update', 'partial_update', 'destroy']:
            # Check write permissions
            return check_object_write_access(obj, request.user)
        # All other actions are allowed for public events.
        return True
