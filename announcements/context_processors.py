from cosinnus.conf import settings

from .models import Announcement


def add_custom_announcements(request):
    context = dict()
    if not settings.COSINNUS_V3_FRONTEND_EVERYWHERE_ENABLED:
        # in v3 the announcements are shown in the frontend provided by the 'api-portal-settings' API.
        context['custom_announcements'] = Announcement.objects.active()
    return context
