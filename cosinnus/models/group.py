# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import re
import six

from django.core.cache import cache
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

MEMBER_STATUS = (MEMBERSHIP_MEMBER, MEMBERSHIP_ADMIN,)


_GROUPS_SLUG_CACHE_KEY = 'cosinnus/core/groups/slugs'
_GROUPS_ID_CACHE_KEY = 'cosinnus/core/groups/ids'
_GROUP_CACHE_KEY = 'cosinnus/core/group/%s'
_MEMBERSHIP_ADMINS_KEY = 'cosinnus/core/membership/admins/%d'
_MEMBERSHIP_MEMBERS_KEY = 'cosinnus/core/membership/members/%d'
_MEMBERSHIP_PENDINGS_KEY = 'cosinnus/core/membership/pendings/%d'


def group_name_validator(value):
    RegexValidator(
        re.compile('^[^/]+$'),
        _('Enter a valid group name. Forward slash is not allowed.'),
        'invalid'
    )(value)


class CosinnusGroupManager(models.Manager):

    use_for_related_fields = True

    def get_slugs(self):
        slugs = cache.get(_GROUPS_SLUG_CACHE_KEY)
        if slugs is None:
            slugs = dict(self.values_list('slug', 'id').all())
            ids = dict((v, k) for k, v in six.iteritems(slugs))
            cache.set(_GROUPS_SLUG_CACHE_KEY, slugs)
            cache.set(_GROUPS_ID_CACHE_KEY, ids)
        return slugs

    def get_ids(self):
        ids = cache.get(_GROUPS_ID_CACHE_KEY)
        if ids is None:
            ids = dict(self.values_list('id', 'slug').all())
            slugs = dict((v, k) for k, v in six.iteritems(ids))
            cache.set(_GROUPS_ID_CACHE_KEY, ids)
            cache.set(_GROUPS_SLUG_CACHE_KEY, slugs)
        return ids

    def get_cached(self, slugs=None, ids=None):
        # Check that only one of slug and slugs is set:
        if slugs is None and ids is None:
            slugs = self.get_slugs()

        if slugs:
            if isinstance(slugs, six.string_types):
                # We request a single group
                slug = slugs
                group = cache.get(_GROUP_CACHE_KEY % slug)
                if group is None:
                    group = super(CosinnusGroupManager, self).get(slug=slug)
                    cache.set(_GROUP_CACHE_KEY % group.slug, group)
                return group
            else:
                # We request multiple groups by slugs
                keys = set([_GROUP_CACHE_KEY % s for s in slugs])
                groups = cache.get_many(keys)

                missing = [key.split('/')[-1] for key in keys if key not in groups]
                if missing:
                    query = self.get_query_set()
                    if not len(missing) == len(keys):
                        query = query.filter(slug__in=missing)
                    for group in query:
                        groups[_GROUP_CACHE_KEY % group.slug] = group
                    cache.set_many(groups, 300)
                return groups.values()
        else:
            if isinstance(slugs, int):
                # We request a single group
                cached_ids = self.get_ids()
                slug = cached_ids.get(ids, None)
                if slug:
                    return self.get_cached(slugs=slug)
                return None  # We rely on the slug and id maps being up to date
            else:
                # We request multiple groups
                cached_ids = self.get_ids()
                slugs = filter(None, (cached_ids.get(id, None) for id in ids))
                if slugs:
                    return self.get_cached(slugs=slugs)
                return []  # We rely on the slug and id maps being up to date

    def get(self, slug=None):
        return self.get_cached(slugs=slug)

    def get_for_user(self, user):
        ids = self.filter(memberships__status__in=MEMBER_STATUS,
                          memberships__user_id=user.pk).values_list('id', flat=True)
        return self.get_cached(ids=ids)

    def public(self):
        for group in self.get_cached():
            if group.public:
                yield group


class CosinnusGroupMembershipManager(models.Manager):

    use_for_related_fields = True

    def get_admins(self, group):
        pk = isinstance(group, int) and group or group.pk
        uids = cache.get(_MEMBERSHIP_ADMINS_KEY % pk)
        if uids is None:
            uids = set(self.filter(group_id=pk, status=MEMBERSHIP_ADMIN)
                           .values_list('user_id', flat=True).all())
            cache.set(_MEMBERSHIP_ADMINS_KEY % pk, uids)
        return uids

    def get_members(self, group):
        pk = isinstance(group, int) and group or group.pk
        uids = cache.get(_MEMBERSHIP_MEMBERS_KEY % pk)
        if uids is None:
            uids = set(self.filter(group_id=pk, status__in=MEMBER_STATUS)
                           .values_list('user_id', flat=True).all())
            cache.set(_MEMBERSHIP_MEMBERS_KEY % pk, uids)
        return uids

    def get_pendings(self, group):
        pk = isinstance(group, int) and group or group.pk
        uids = cache.get(_MEMBERSHIP_PENDINGS_KEY % pk)
        if uids is None:
            uids = set(self.filter(group_id=pk, status=MEMBERSHIP_PENDING)
                           .values_list('user_id', flat=True).all())
            cache.set(_MEMBERSHIP_PENDINGS_KEY % pk, uids)
        return uids

    # def is_admin(self, user, group):
    #     uid = isinstance(user, int) and user or user.pk
    #     return uid in self.get_admins(group)

    # def is_member(self, user, group):
    #     uid = isinstance(user, int) and user or user.pk
    #     return uid in self.get_members(group)

    # def is_pending(self, user, group):
    #     uid = isinstance(user, int) and user or user.pk
    #     return uid in self.get_pendings(group)


@python_2_unicode_compatible
class CosinnusGroup(models.Model):
    name = models.CharField(_('Name'), max_length=100,
        validators=[group_name_validator])
    slug = models.SlugField(_('Slug'), max_length=50)
    public = models.BooleanField(_('Public'), default=False)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True,
        related_name='cosinnus_groups', through='CosinnusGroupMembership')

    objects = CosinnusGroupManager()

    class Meta:
        app_label = 'cosinnus'
        ordering = ('name',)
        verbose_name = _('Cosinnus group')
        verbose_name_plural = _('Cosinnus groups')

    def __init__(self, *args, **kwargs):
        super(CosinnusGroup, self).__init__(*args, **kwargs)
        self._admins = None
        self._members = None
        self._pendings = None

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        slugs = [self.slug] if self.slug else []
        unique_aware_slugify(self, 'name', 'slug')
        super(CosinnusGroup, self).save(*args, **kwargs)
        slugs.append(self.slug)
        self._clear_cache(slug=self.slug)

    def is_admin(self, user):
        if self._admins is None:
            self._admins = CosinnusGroupMembership.objects.get_admins(self.pk)
        uid = isinstance(user, int) and user or user.pk
        return uid in self._admins

    def is_member(self, user):
        if self._members is None:
            self._members = CosinnusGroupMembership.objects.get_members(self.pk)
        uid = isinstance(user, int) and user or user.pk
        return uid in self._members

    def is_pending(self, user):
        if self._pendings is None:
            self._pendings = CosinnusGroupMembership.objects.get_pendings(self.pk)
        uid = isinstance(user, int) and user or user.pk
        return uid in self._pendings

    def _clear_cache(self, slug=None, slugs=None):
        # TODO: clear membership caches
        keys = [
            _GROUPS_SLUG_CACHE_KEY,
            _GROUPS_ID_CACHE_KEY,
        ]
        if slug:
            keys.append(_GROUP_CACHE_KEY % slug)
        if slugs:
            keys.extend([_GROUP_CACHE_KEY % s for s in slugs])
        cache.delete_many(keys)


@python_2_unicode_compatible
class CosinnusGroupMembership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
        related_name='cosinnus_memberships')
    group = models.ForeignKey(CosinnusGroup, related_name='memberships')
    status = models.PositiveSmallIntegerField(choices=MEMBERSHIP_STATUSES,
        db_index=True, default=MEMBERSHIP_PENDING)
    date = models.DateTimeField(auto_now_add=True, editable=False)

    objects = CosinnusGroupMembershipManager()

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

    def delete(self, *args, **kwargs):
        self._clear_cache()
        super(CosinnusGroupMembership, self).delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        # Only update the date if the the state changes from pending to member
        # or admin
        if self._old_current_status == MEMBERSHIP_PENDING and \
                self.status != self._old_current_status:
            self.date = now()
        super(CosinnusGroupMembership, self).save(*args, **kwargs)
        self._clear_cache()

    def _clear_cache(self):
        cache.delete_many([
            _MEMBERSHIP_ADMINS_KEY % self.group.pk,
            _MEMBERSHIP_MEMBERS_KEY % self.group.pk,
            _MEMBERSHIP_PENDINGS_KEY % self.group.pk,
        ])
