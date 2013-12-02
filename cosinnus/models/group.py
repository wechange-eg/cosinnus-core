# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re

from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import m2m_changed
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings
from cosinnus.utils.functions import unique_aware_slugify


def group_name_validator(value):
    RegexValidator(
        re.compile('^[^/]+$'),
        _('Enter a valid group name. Forward slash is not allowed.'),
        'invalid'
    )(value)


class CosinnusGroupQuerySet(models.query.QuerySet):

    def public(self):
        return self.filter(public=True)


class CosinnusGroupManager(models.Manager):

    use_for_related_fields = True

    def get_query_set(self):
        return CosinnusGroupQuerySet(self.model, using=self._db)

    def public(self):
        return self.get_query_set().public()


@python_2_unicode_compatible
class CosinnusGroup(models.Model):
    name = models.CharField(_('Name'), max_length=100,
        validators=[group_name_validator])
    slug = models.SlugField(_('Slug'), max_length=50)
    public = models.BooleanField(_('Public'), default=False)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL,
        related_name='cosinnus_groups', blank=True)

    objects = CosinnusGroupManager()

    class Meta:
        app_label = 'cosinnus'
        verbose_name = _('Cosinnus group')
        verbose_name_plural = _('Cosinnus groups')

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        unique_aware_slugify(self, 'name', 'slug')
        super(CosinnusGroup, self).save(*args, **kwargs)


@python_2_unicode_compatible
class GroupAdmin(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('User'),
        null=False, blank=False, on_delete=models.CASCADE)
    group = models.ForeignKey(CosinnusGroup, verbose_name=_('Group'),
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
        except ImportError:
            from django.db.transaction import commit_on_success
            context_wrapper = commit_on_success
        with context_wrapper():
            super(GroupAdmin, self).save(*args, **kwargs)
            if not self.user.cosinnus_groups.filter(id=self.group_id).exists():
                self.user.cosinnus_groups.add(self.group)


# Due to a bug in Django (#6707) this does not work (yet). E.g. Django admin
# does not send the post_remove action
def cleanup_group_admin(sender, **kwargs):
    if kwargs.get('action', None) == 'post_remove':
        instance = kwargs.get('instance', None)
        pk_set = kwargs.get('pk_set', set())
        if instance.pk and pk_set:
            GroupAdmin.objects.filter(group_id=instance.pk,
                                      user_id__in=pk_set).delete()

m2m_changed.connect(cleanup_group_admin, sender=CosinnusGroup.users.through)
