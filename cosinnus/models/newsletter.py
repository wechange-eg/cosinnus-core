from django.db import models

from cosinnus.conf import settings

class Newsletter(models.Model):

    subject = models.CharField(max_length=300)
    body = models.TextField()
    recipients_source = models.CharField(max_length=100, blank=True)
    sent = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.subject