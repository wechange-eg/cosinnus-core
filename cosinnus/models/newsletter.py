from django.db import models

from cosinnus.conf import settings
from cosinnus.models.managed_tags import CosinnusManagedTag


class BaseNewsletter(models.Model):
    subject = models.CharField(max_length=300)
    body = models.TextField()
    sent = models.DateTimeField(blank=True, null=True)
    is_sending = models.BooleanField(default=False)
    queued_mail = models.OneToOneField('cosinnus.QueuedMassMail', on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.subject


class Newsletter(BaseNewsletter):
    managed_tags = models.ManyToManyField(CosinnusManagedTag)


class GroupsNewsletter(BaseNewsletter):
    groups = models.ManyToManyField(settings.COSINNUS_GROUP_OBJECT_MODEL, blank=True, related_name='+')
