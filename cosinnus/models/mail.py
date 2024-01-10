import logging

from django.db import models
from django.utils.translation import gettext_lazy as _
from cosinnus.conf import settings


logger = logging.getLogger('cosinnus')


class QueuedMassMail(models.Model):
    subject = models.CharField(max_length=300, verbose_name=_('Subject'))
    content = models.TextField(verbose_name=_('Content'))
    recipients = models.ManyToManyField(settings.AUTH_USER_MODEL, verbose_name=_('Recipients'),
                                        related_name='queued_mass_mails')
    recipients_sent = models.ManyToManyField(settings.AUTH_USER_MODEL, verbose_name=_('Mails sent to Recipients'),
                                             related_name='queued_mass_mails_sent')
    send_mail_kwargs = models.JSONField(default=dict, null=True, blank=True, verbose_name=_('Mail function kwargs'))
    created = models.DateTimeField(auto_now_add=True, editable=False, verbose_name=_('Created'))
    sending_in_progress = models.BooleanField(default=False, verbose_name=_('Sending in Progress'))

    class Meta:
        verbose_name = _('Queued Mass Mail')
        verbose_name_plural = _('Queued Mass Mails')
        ordering = ['-created']

    def __str__(self):
        return self.subject

