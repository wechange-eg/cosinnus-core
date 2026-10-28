from .models import Announcement


def add_custom_announcements(request):
    context = dict()
    context['custom_announcements'] = Announcement.objects.active()
    return context
