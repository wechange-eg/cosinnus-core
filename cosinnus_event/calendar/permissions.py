from rest_framework.permissions import BasePermission

from cosinnus.utils.permissions import (
    check_group_create_objects_access,
    check_object_read_access,
    check_object_write_access,
)


class CalendarPublicEventPermissions(BasePermission):
    """Permissions for the calendar events viewset."""

    # List of viewset actions that require write access to the event.
    EVENT_WRITE_ACTIONS = [
        'update',
        'partial_update',
        'destroy',
        'attach_file',
        'delete_attached_file',
        'bbb_room',
    ]

    # List of viewset actions that require the user to be logged in.
    EVENT_LOGGED_IN_ACTIONS = ['attendance']

    # List of vieset actions allowed by anonymous users.
    EVENT_ANONYOUNS_ACTIONS = [
        None,  # action is not set by DRF for OPTIONS requests
        'retrieve',
        'bbb_room_urls',
    ]

    def has_permission(self, request, view):
        if view.action == 'list':
            # Listing of public events is allowed for group members
            return check_object_read_access(view.group, request.user)
        elif view.action == 'create':
            # Check create permission for user in the group
            return check_group_create_objects_access(view.group, request.user)
        # Return True, permissions for other operations are check per object in has_object_permission.
        return True

    def has_object_permission(self, request, view, obj):
        if view.action in self.EVENT_WRITE_ACTIONS:
            # Check write permissions
            return check_object_write_access(obj, request.user)
        elif view.action in self.EVENT_LOGGED_IN_ACTIONS:
            # Check user is logged in
            return request.user.is_authenticated
        elif view.action in self.EVENT_ANONYOUNS_ACTIONS:
            # public actions
            return True
        raise NotImplementedError(f'Unhandled calendar API permissions for action: {view.action}')
