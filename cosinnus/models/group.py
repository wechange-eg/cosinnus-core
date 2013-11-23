# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import Group
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings


@python_2_unicode_compatible
class GroupAdmin(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('User'),
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

    def save(self, *args, **kwargs):
        """Atomically add the user to the group if not already a member"""
        # TODO: Drop ImportError check when Django 1.5 support is dropped
        try:
            from django.db.transaction import atomic
            context_wrapper = atomic
        except ImportError as e:
            from django.db.transaction import commit_on_success
            context_wrapper = commit_on_success
        with context_wrapper():
            super(GroupAdmin, self).save(*args, **kwargs)
            if not self.user.groups.filter(id=self.group_id).exists():
                self.user.groups.add(self.group)
