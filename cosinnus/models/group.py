# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import OrderedDict
import re
import six

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _, pgettext_lazy as p_

from taggit.managers import TaggableManager
from tinymce.models import HTMLField

from cosinnus.conf import settings
from cosinnus.utils.functions import unique_aware_slugify


#: Role defining a user has requested to be added to a group
MEMBERSHIP_PENDING = 0

#: Role defining a user is a member but not an admin of a group
MEMBERSHIP_MEMBER = 1

#: Role defining a user is an admin of a group
MEMBERSHIP_ADMIN = 2

MEMBERSHIP_STATUSES = (
    (MEMBERSHIP_PENDING, p_('cosinnus membership status', 'pending')),
    (MEMBERSHIP_MEMBER, p_('cosinnus membership status', 'member')),
    (MEMBERSHIP_ADMIN, p_('cosinnus membership status', 'admin')),
)

#: A user is a member of a group if either is an explicit member or admin
MEMBER_STATUS = (MEMBERSHIP_MEMBER, MEMBERSHIP_ADMIN,)


_GROUPS_SLUG_CACHE_KEY = 'cosinnus/core/groups/slugs'
_GROUPS_PK_CACHE_KEY = 'cosinnus/core/groups/pks'
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


class CosinnusGroupQS(models.query.QuerySet):

    def filter_membership_status(self, status):
        if isinstance(status, (list, tuple)):
            return self.filter(memberships__status__in=status)
        return self.filter(memberships__status=status)

    def update(self, **kwargs):
        ret = super(CosinnusGroupQS, self).update(**kwargs)
        self.model._clear_cache()
        return ret


class CosinnusGroupMembershipQS(models.query.QuerySet):

    def filter_membership_status(self, status):
        if isinstance(status, (list, tuple)):
            return self.filter(status__in=status)
        return self.filter(status=status)

    def update(self, **kwargs):
        ret = super(CosinnusGroupMembershipQS, self).update(**kwargs)
        self.model._clear_cache()
        return ret


class CosinnusGroupManager(models.Manager):

    use_for_related_fields = True

    def get_queryset(self):
        return CosinnusGroupQS(self.model, using=self._db)

    get_query_set = get_queryset

    def filter_membership_status(self, status):
        return self.get_queryset().filter_membership_status(status)

    def get_slugs(self):
        """
        Gets all group slugs from the cache or, if the can has not been filled,
        gets the slugs and pks from the database and fills the cache.

        :returns: A :class:`OrderedDict` with a `slug => pk` mapping of all
            groups
        """
        slugs = cache.get(_GROUPS_SLUG_CACHE_KEY)
        if slugs is None:
            slugs = OrderedDict(self.values_list('slug', 'id').all())
            pks = OrderedDict((v, k) for k, v in six.iteritems(slugs))
            cache.set(_GROUPS_SLUG_CACHE_KEY, slugs,
                settings.COSINNUS_GROUP_CACHE_TIMEOUT)
            cache.set(_GROUPS_PK_CACHE_KEY, pks,
                settings.COSINNUS_GROUP_CACHE_TIMEOUT)
        return slugs

    def get_pks(self):
        """
        Gets all group pks from the cache or, if the can has not been filled,
        gets the pks and slugs from the database and fills the cache.

        :returns: A :class:`OrderedDict` with a `pk => slug` mapping of all
            groups
        """
        pks = cache.get(_GROUPS_PK_CACHE_KEY)
        if pks is None:
            pks = OrderedDict(self.values_list('id', 'slug').all())
            slugs = OrderedDict((v, k) for k, v in six.iteritems(pks))
            cache.set(_GROUPS_PK_CACHE_KEY, pks,
                settings.COSINNUS_GROUP_CACHE_TIMEOUT)
            cache.set(_GROUPS_SLUG_CACHE_KEY, slugs,
                settings.COSINNUS_GROUP_CACHE_TIMEOUT)
        return pks

    def get_cached(self, slugs=None, pks=None):
        """
        Gets all groups defined by either `slugs` or `pks`.

        `slugs` and `pks` may be a list or tuple of identifiers to use for
        request where the elements are of type string / unicode or int,
        respectively. You may provide a single string / unicode or int directly
        to query only one object.

        :returns: An instance or a list of instances of :class:`CosinnusGroup`.
        :raises: If a single object is defined a `CosinnusGroup.DoesNotExist`
            will be raised in case the requested object does not exist.
        """
        # Check that at most one of slugs and pks is set
        assert not (slugs and pks)
        if (slugs is None) and (pks is None):
            slugs = list(self.get_slugs().keys())

        if slugs is not None:
            if isinstance(slugs, six.string_types):
                # We request a single group
                slug = slugs
                group = cache.get(_GROUP_CACHE_KEY % slug)
                if group is None:
                    group = super(CosinnusGroupManager, self).get(slug=slug)
                    cache.set(_GROUP_CACHE_KEY % group.slug, group,
                        settings.COSINNUS_GROUP_CACHE_TIMEOUT)
                return group
            else:
                # We request multiple groups by slugs
                keys = [_GROUP_CACHE_KEY % s for s in slugs]
                groups = cache.get_many(keys)
                missing = [key.split('/')[-1] for key in keys if key not in groups]
                if missing:
                    query = self.get_queryset().filter(slug__in=missing)
                    for group in query:
                        groups[_GROUP_CACHE_KEY % group.slug] = group
                    cache.set_many(groups, settings.COSINNUS_GROUP_CACHE_TIMEOUT)
                return sorted(groups.values(), key=lambda x: x.name)
        elif pks is not None:
            if isinstance(pks, int):
                # We request a single group
                cached_pks = self.get_pks()
                slug = cached_pks.get(pks, None)
                if slug:
                    return self.get_cached(slugs=slug)
                return None  # We rely on the slug and id maps being up to date
            else:
                # We request multiple groups
                cached_pks = self.get_pks()
                slugs = filter(None, (cached_pks.get(id, []) for id in pks))
                if slugs:
                    return self.get_cached(slugs=slugs)
                return []  # We rely on the slug and id maps being up to date
        return []

    def get(self, slug=None):
        return self.get_cached(slugs=slug)

    def get_for_user(self, user):
        """
        :returns: a list of :class:`CosinnusGroup` the given user is a member
            or admin of.
        """
        pks = self.filter(memberships__user_id=user.pk) \
                  .filter_membership_status(MEMBER_STATUS) \
                  .values_list('id', flat=True).distinct()
        return self.get_cached(pks=pks)

    def public(self):
        """
        :returns: An iterator over all public groups.
        """
        for group in self.get_cached():
            if group.public:
                yield group


class CosinnusGroupMembershipManager(models.Manager):

    use_for_related_fields = True

    def get_queryset(self):
        return CosinnusGroupMembershipQS(self.model, using=self._db)

    get_query_set = get_queryset

    def filter_membership_status(self, status):
        return self.get_queryset().filter_membership_status(status)

    def _get_users_for_single_group(self, group_id, cache_key, status):
        uids = cache.get(cache_key % group_id)
        if uids is None:
            query = self.filter(group_id=group_id).filter_membership_status(status)
            uids = list(query.values_list('user_id', flat=True).all())
            cache.set(cache_key % group_id, uids)
        return uids

    def _get_users_for_multiple_groups(self, group_ids, cache_key, status):
        keys = [cache_key % g for g in group_ids]
        users = cache.get_many(keys)
        missing = list(map(int, (key.split('/')[-1] for key in keys if key not in users)))
        if missing:
            _q = self.filter_membership_status(status).values_list('user_id', flat=True)
            for group in missing:
                uids = list(_q._clone().filter(group_id=group).all())
                users[cache_key % group] = uids
            cache.set_many(users)
        return {int(k.split('/')[-1]): v for k, v in six.iteritems(users)}

    def get_admins(self, group=None, groups=None):
        """
        Given either a group or a list of groups, this function returns all
        members with the :data:`MEMBERSHIP_ADMIN` role.
        """
        assert (group is None) ^ (groups is None)
        if group:
            gid = isinstance(group, int) and group or group.pk
            return self._get_users_for_single_group(gid, _MEMBERSHIP_ADMINS_KEY, MEMBERSHIP_ADMIN)
        else:
            gids = [isinstance(g, int) and g or g.pk for g in groups]
            return self._get_users_for_multiple_groups(gids, _MEMBERSHIP_ADMINS_KEY, MEMBERSHIP_ADMIN)

    def get_members(self, group=None, groups=None):
        """
        Given either a group or a list of groups, this function returns all
        members with the :data:`MEMBERSHIP_MEMBER` role.
        """
        assert (group is None) ^ (groups is None)
        if group:
            gid = isinstance(group, int) and group or group.pk
            return self._get_users_for_single_group(gid, _MEMBERSHIP_MEMBERS_KEY, MEMBER_STATUS)
        else:
            gids = [isinstance(g, int) and g or g.pk for g in groups]
            return self._get_users_for_multiple_groups(gids, _MEMBERSHIP_MEMBERS_KEY, MEMBER_STATUS)

    def get_pendings(self, group=None, groups=None):
        """
        Given either a group or a list of groups, this function returns all
        members with the :data:`MEMBERSHIP_PENDING` role.
        """
        assert (group is None) ^ (groups is None)
        if group:
            gid = isinstance(group, int) and group or group.pk
            return self._get_users_for_single_group(gid, _MEMBERSHIP_PENDINGS_KEY, MEMBERSHIP_PENDING)
        else:
            gids = [isinstance(g, int) and g or g.pk for g in groups]
            return self._get_users_for_multiple_groups(gids, _MEMBERSHIP_PENDINGS_KEY, MEMBERSHIP_PENDING)


@python_2_unicode_compatible
class CosinnusGroup(models.Model):
    name = models.CharField(_('Name'), max_length=100,
        validators=[group_name_validator])
    slug = models.SlugField(_('Slug'), max_length=50, unique=True, blank=True)
    description = HTMLField(verbose_name=_('Description'), blank=True)
    public = models.BooleanField(_('Public'), default=False)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True,
        related_name='cosinnus_groups', through='CosinnusGroupMembership')
    media_tag = models.OneToOneField(settings.COSINNUS_TAG_OBJECT_MODEL,
        blank=True, null=True, on_delete=models.PROTECT)
    tags = TaggableManager(_('Tags'), blank=True)

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

    def delete(self, *args, **kwargs):
        super(CosinnusGroup, self).delete(*args, **kwargs)
        self._clear_cache()

    def save(self, *args, **kwargs):
        slugs = [self.slug] if self.slug else []
        unique_aware_slugify(self, 'name', 'slug')
        if not self.slug:
            raise ValidationError(_('Slug must not be empty.'))
        super(CosinnusGroup, self).save(*args, **kwargs)
        slugs.append(self.slug)
        self._clear_cache(slug=self.slug)

    @property
    def admins(self):
        if self._admins is None:
            self._admins = CosinnusGroupMembership.objects.get_admins(self.pk)
        return self._admins

    def is_admin(self, user):
        """Checks whether the given user is an admin of this group"""
        uid = isinstance(user, int) and user or user.pk
        return uid in self.admins

    @property
    def members(self):
        if self._members is None:
            self._members = CosinnusGroupMembership.objects.get_members(self.pk)
        return self._members

    def is_member(self, user):
        """Checks whether the given user is a member of this group"""
        uid = isinstance(user, int) and user or user.pk
        return uid in self.members

    @property
    def pendings(self):
        if self._pendings is None:
            self._pendings = CosinnusGroupMembership.objects.get_pendings(self.pk)
        return self._pendings

    def is_pending(self, user):
        """Checks whether the given user has a pending status on this group"""
        uid = isinstance(user, int) and user or user.pk
        return uid in self.pendings

    @classmethod
    def _clear_cache(self, slug=None, slugs=None):
        keys = [
            _GROUPS_SLUG_CACHE_KEY,
            _GROUPS_PK_CACHE_KEY,
        ]
        if slug:
            keys.append(_GROUP_CACHE_KEY % slug)
        if slugs:
            keys.extend([_GROUP_CACHE_KEY % s for s in slugs])
        cache.delete_many(keys)
        if isinstance(self, CosinnusGroup):
            self._clear_local_cache()

    def _clear_local_cache(self):
        self._admins = self._members = self._pendings = None


@python_2_unicode_compatible
class CosinnusGroupMembership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
        related_name='cosinnus_memberships', on_delete=models.CASCADE)
    group = models.ForeignKey(CosinnusGroup, related_name='memberships',
        on_delete=models.CASCADE)
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
        super(CosinnusGroupMembership, self).delete(*args, **kwargs)
        self._clear_cache()

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
        self.group._clear_local_cache()
