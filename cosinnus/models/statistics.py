import datetime
import logging

from django.db import models
from django.utils.translation import gettext_lazy as _

from cosinnus.conf import settings

logger = logging.getLogger('cosinnus')


class UserOnlineOnDay(models.Model):
    """A model which signifies with each instance that a given user has been online and used the
    site in an active manner at least once on the given date's day ."""

    date = models.DateField(_('Date'), editable=False, default=datetime.date.today)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, editable=False, related_name='online_days', on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = _('User Online on Day')
        verbose_name_plural = _('User Online on Day')
        ordering = ['-date']
        unique_together = (('date', 'user'),)
