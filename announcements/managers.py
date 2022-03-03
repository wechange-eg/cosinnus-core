from django.db import models


class AnnouncementManager(models.Manager):

    def active(self):
        """
        Returns active announcements
        :return:
        """
        return self.filter(is_active=True)
