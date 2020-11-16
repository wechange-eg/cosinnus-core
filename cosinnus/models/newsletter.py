from django.db import models

from cosinnus.conf import settings
from cosinnus.models.managed_tags import CosinnusManagedTag
from django.contrib.contenttypes.fields import GenericRelation

class Newsletter(models.Model):

    subject = models.CharField(max_length=300)
    body = models.TextField()
    managed_tags = models.ManyToManyField(CosinnusManagedTag)
    sent = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.subject