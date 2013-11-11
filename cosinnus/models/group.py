# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _


@python_2_unicode_compatible
class GroupAdmin(models.Model):
    user = models.ForeignKey(get_user_model(), verbose_name=_('User'),
        null=False, blank=False, on_delete=models.CASCADE)
    group = models.ForeignKey(Group, verbose_name=_('Group'),
        null=False, blank=False, on_delete=models.CASCADE)

    class Meta:
        app_label = 'cosinnus'
        unique_together = ('user', 'group')
        verbose_name = _('Group admin')
        verbose_name_plural = _('Group admins')

    def __str__(self):
        return str(self.user)
