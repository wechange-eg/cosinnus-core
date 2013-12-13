# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re

from django.core.validators import RegexValidator
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _, pgettext_lazy as p_

from cosinnus.conf import settings
from cosinnus.utils.functions import unique_aware_slugify


MEMBERSHIP_PENDING = 0
MEMBERSHIP_MEMBER = 1
MEMBERSHIP_ADMIN = 2

MEMBERSHIP_STATUSES = (
    (MEMBERSHIP_PENDING, p_('cosinnus membership status', 'pending')),
    (MEMBERSHIP_MEMBER, p_('cosinnus membership status', 'member')),
    (MEMBERSHIP_ADMIN, p_('cosinnus membership status', 'admin')),
)


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
    slug = models.SlugField(_('Slug'), max_length=50, unique=True)
    public = models.BooleanField(_('Public'), default=False)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True,
        related_name='cosinnus_groups', through='CosinnusGroupMembership')

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
class CosinnusGroupMembership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    group = models.ForeignKey(CosinnusGroup)
    status = models.PositiveSmallIntegerField(choices=MEMBERSHIP_STATUSES,
        db_index=True, default=MEMBERSHIP_PENDING)
    date = models.DateTimeField(auto_now_add=True, editable=False)

    class Meta:
        app_label = 'cosinnus'
        unique_together = (('user', 'group'),)
        verbose_name = _('Group membership')
        verbose_name_plural = _('Group memberships')

    def __init__(self, *args, **kwargs):
        super(CosinnusGroupMembership, self).__init__(*args, **kwargs)
        self._old_current_status = self.status

    def __str__(self):
        return "<user: %(user)s, group: %(group)s, status: %(status)d>" % {
            'user': self.user,
            'group': self.group,
            'status': self.status,
        }

    def save(self, *args, **kwargs):
        # Only update the date if the the state changes from pending to member
        # or admin
        if self._old_current_status == MEMBERSHIP_PENDING and \
                self.status != self._old_current_status:
            self.date = now()
        super(CosinnusGroupMembership, self).save(*args, **kwargs)

    @property
    def member_since(self):
        if self.status != MEMBERSHIP_PENDING:
            return self.date
        return None

    @property
    def is_pending(self):
        return self.status == MEMBERSHIP_PENDING

    @property
    def is_member(self):
        return self.status != MEMBERSHIP_PENDING

    @property
    def is_admin(self):
        return self.status == MEMBERSHIP_ADMIN
