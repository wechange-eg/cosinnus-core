from __future__ import unicode_literals

from django.conf import settings

from postman.models import Message


def inbox(request):
    """Provide the count of unread messages for an authenticated user."""
    # only do this if we are actually using it as main messaged module in cosinnus.
    # skip if rocket is enabled or postman is in archive mode
    if not getattr(settings, 'COSINNUS_POSTMAN_ARCHIVE_MODE', False) and not getattr(
        settings, 'COSINNUS_ROCKET_ENABLED', False
    ):
        if request.user.is_authenticated:
            return {'postman_unread_count': Message.objects.inbox_unread_count(request.user)}
    return {}
