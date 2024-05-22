import logging

from django.db import models
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger('cosinnus')


class TemporaryData(models.Model):
    created = models.DateTimeField(verbose_name=_('Created'), editable=False, auto_now_add=True)
    deletion_after = models.DateTimeField(verbose_name=_('Deletion after'))
    description = models.CharField(max_length=255, verbose_name=_('Description'))
    data = models.BinaryField(verbose_name=_('Data'))

    class Meta:
        verbose_name = _('Temporary Data')
        verbose_name_plural = _('Temporary Data')
        ordering = ['-created']
