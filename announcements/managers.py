from django.db import models


class AnnouncementManager(models.Manager):
    def active(self):
        """
        Returns active announcements
        :return:
        """
        return self.filter(is_active=True)

    def active_for_session(self, request):
        """Get active user announcements considering dismissed announcements saved in the user session."""
        announcements = self.active()
        dismissed = request.session.get(self.model.SESSION_DISMISSED_KEY, [])
        announcements = announcements.exclude(pk__in=dismissed)
        return announcements
