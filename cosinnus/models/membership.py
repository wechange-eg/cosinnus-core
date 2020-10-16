import six
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _, pgettext_lazy as p_

#: Role defining a user has requested to be added to a group
from cosinnus.utils.user import filter_active_users

MEMBERSHIP_PENDING = 0

#: Role defining a user is a member but not an admin of a group
MEMBERSHIP_MEMBER = 1

#: Role defining a user is an admin of a group
MEMBERSHIP_ADMIN = 2

#: Role defining a user was added to a group and must confirm this before becoming a member
MEMBERSHIP_INVITED_PENDING = 3

MEMBERSHIP_STATUSES = (
    (MEMBERSHIP_PENDING, p_('cosinnus membership status', 'pending')),
    (MEMBERSHIP_MEMBER, p_('cosinnus membership status', 'member')),
    (MEMBERSHIP_ADMIN, p_('cosinnus membership status', 'admin')),
    (MEMBERSHIP_INVITED_PENDING, p_('cosinnus membership status', 'pending-invited')),
)

#: A user is a member of a group if either is an explicit member or admin
MEMBER_STATUS = (MEMBERSHIP_MEMBER, MEMBERSHIP_ADMIN,)

_MEMBERSHIP_ADMINS_KEY = 'cosinnus/core/membership/%s/admins/%d'
_MEMBERSHIP_MEMBERS_KEY = 'cosinnus/core/membership/%s/members/%d'
_MEMBERSHIP_PENDINGS_KEY = 'cosinnus/core/membership/%s/pendings/%d'
_MEMBERSHIP_INVITED_PENDINGS_KEY = 'cosinnus/core/membership/%s/invited_pendings/%d'


class CosinnusGroupMembershipQS(models.query.QuerySet):

    def filter_membership_status(self, status):
        if isinstance(status, (list, tuple)):
            return self.filter(status__in=status)
        return self.filter(status=status)

    def update(self, **kwargs):
        ret = super(CosinnusGroupMembershipQS, self).update(**kwargs)
        self.model._clear_cache()
        return ret


class BaseMembershipManager(models.Manager):

    """ Note: Thismanager is used for all Groups, and also Portals! """

    use_for_related_fields = True

    def get_queryset(self):
        return CosinnusGroupMembershipQS(self.model, using=self._db)

    get_query_set = get_queryset

    def filter_membership_status(self, status):
        return self.get_queryset().filter_membership_status(status)

    def _get_users_for_single_group(self, group_id, cache_key, status):
        key = cache_key % (self.model.CACHE_KEY_MODEL, group_id)
        uids = cache.get(key)
        if uids is None:
            query = self.filter(group_id=group_id).filter_membership_status(status)
            uids = list(query.values_list('user_id', flat=True).all())
            cache.set(key, uids, settings.COSINNUS_GROUP_MEMBERSHIP_CACHE_TIMEOUT)
            """ TODO: FIXME: bc of some bug, this cache key is often reset/cleared and read in again on each query!! 
                            The cache on this key seems not to get cleared from code, so no clue what's going on here. """
        return uids

    def _get_users_for_multiple_groups(self, group_ids, cache_key, status):
        keys = [cache_key % (self.model.CACHE_KEY_MODEL, g) for g in group_ids]
        users = cache.get_many(keys)
        missing = list(map(int, (key.split('/')[-1] for key in keys if key not in users)))
        if missing:
            _q = self.filter_membership_status(status).values_list('user_id', flat=True)
            for group in missing:
                uids = list(_q._clone().filter(group_id=group).all())
                users[cache_key % (self.model.CACHE_KEY_MODEL, group)] = uids
            cache.set_many(users, settings.COSINNUS_GROUP_MEMBERSHIP_CACHE_TIMEOUT)
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
        members with the :data:`MEMBERSHIP_MEMBER` OR `MEMBERSHIP_ADMIN` role.
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

    def get_invited_pendings(self, group=None, groups=None):
        """
        Given either a group or a list of groups, this function returns all
        members with the :data:`MEMBERSHIP_INVITED_PENDING` role.
        """
        assert (group is None) ^ (groups is None)
        if group:
            gid = isinstance(group, int) and group or group.pk
            return self._get_users_for_single_group(gid, _MEMBERSHIP_INVITED_PENDINGS_KEY, MEMBERSHIP_INVITED_PENDING)
        else:
            gids = [isinstance(g, int) and g or g.pk for g in groups]
            return self._get_users_for_multiple_groups(gids, _MEMBERSHIP_INVITED_PENDINGS_KEY,
                                                       MEMBERSHIP_INVITED_PENDING)


@python_2_unicode_compatible
class BaseMembership(models.Model):
    # group = must be defined in overriding class!
    # user = must be defined in overriding class!
    status = models.PositiveSmallIntegerField(choices=MEMBERSHIP_STATUSES,
        db_index=True, default=MEMBERSHIP_PENDING)
    date = models.DateTimeField(auto_now_add=True, editable=False)
    # moderator status for portals, unused for groups as of now
    is_moderator = models.BooleanField(_('Is Moderator'), default=False)

    objects = BaseMembershipManager()

    CACHE_KEY_MODEL = None

    class Meta(object):
        abstract = True
        app_label = 'cosinnus'
        unique_together = (('user', 'group'),)

    def __init__(self, *args, **kwargs):
        if not self.CACHE_KEY_MODEL:
            raise ImproperlyConfigured('You must define a cache key specific to ' +
                '                        the model of this membership type!')
        super(BaseMembership, self).__init__(*args, **kwargs)
        self._old_current_status = self.status

    def __str__(self):
        return "<user: %(user)s, group: %(group)s, status: %(status)d>" % {
            'user': getattr(self, 'user', None),
            'group': getattr(self, 'group', None),
            'status': self.status,
        }

    def delete(self, *args, **kwargs):
        super(BaseMembership, self).delete(*args, **kwargs)
        # run an empty save on user so userprofile search indices get updated with new memberships through signals
        self.user.cosinnus_profile.save()
        self._clear_cache()

    def save(self, *args, **kwargs):
        # Only update the date if the the state changes from pending to member
        # or admin
        if (self._old_current_status == MEMBERSHIP_PENDING or self._old_current_status == MEMBERSHIP_INVITED_PENDING) and \
                (self.status == MEMBERSHIP_ADMIN or self.status == MEMBERSHIP_MEMBER):
            self.date = now()
        super(BaseMembership, self).save(*args, **kwargs)
        # run an empty save on user so userprofile search indices get updated with new memberships through signals
        if hasattr(self, 'user'):
            self.user.cosinnus_profile.save()
        self._clear_cache()

    def _clear_cache(self):
        self.clear_member_cache_for_group(self.group)

    @classmethod
    def clear_member_cache_for_group(cls, group):
        keys = [
            _MEMBERSHIP_ADMINS_KEY % (cls.CACHE_KEY_MODEL, group.pk),
            _MEMBERSHIP_MEMBERS_KEY % (cls.CACHE_KEY_MODEL, group.pk),
            _MEMBERSHIP_PENDINGS_KEY % (cls.CACHE_KEY_MODEL, group.pk),
            _MEMBERSHIP_INVITED_PENDINGS_KEY % (cls.CACHE_KEY_MODEL, group.pk),
        ]
        cache.delete_many(keys)
        group._clear_local_cache()

    def user_email(self):
        return self.user.email


class MembershipClassMixin(object):
    membership_class = None


class MembersManagerMixin(object):
    membership_class = None

    @property
    def admins(self):
        return self.membership_class.objects.get_admins(self.pk)

    @property
    def actual_admins(self):
        """ Returns a QS of users that are admins of this group and are actually active and visible on the site """
        qs = get_user_model().objects.filter(id__in=self.admins)
        qs = filter_active_users(qs)
        return qs

    def is_admin(self, user):
        """Checks whether the given user is an admin of this group"""
        uid = isinstance(user, int) and user or user.pk
        return uid in self.admins

    @property
    def members(self):
        """ Returns a list of user ids that are members of this group, no matter if active or not """
        return self.membership_class.objects.get_members(self.pk)

    @property
    def actual_members(self):
        """ Returns a QS of users that are members of this group and are actually active and visible on the site """
        qs = get_user_model().objects.filter(id__in=self.members)
        qs = filter_active_users(qs)
        return qs

    @property
    def member_count(self):
        """ Returns a count of this group's active members (users that are active and have logged in) """
        return self.actual_members.count()

    def is_member(self, user):
        """Checks whether the given user is a member of this group"""
        uid = isinstance(user, int) and user or user.pk
        return uid in self.members

    @property
    def pendings(self):
        return self.membership_class.objects.get_pendings(self.pk)

    def is_pending(self, user):
        """Checks whether the given user has a pending status on this group"""
        uid = isinstance(user, int) and user or user.pk
        return uid in self.pendings

    @property
    def actual_pendings(self):
        """ Returns a QS of users that have a pending status on this group and are actually active and visible on the site """
        qs = get_user_model().objects.filter(id__in=self.pendings)
        qs = filter_active_users(qs)
        return qs

    @property
    def invited_pendings(self):
        """ Returns a QS of users that have a pending invitation on this group """
        return self.membership_class.objects.get_invited_pendings(self.pk)

    def is_invited_pending(self, user):
        """Checks whether the given user has a pending invitation status on this group"""
        uid = isinstance(user, int) and user or user.pk
        return uid in self.invited_pendings

    @property
    def actual_invited_pendings(self):
        """ Returns a QS of users that have a pending invitation on this group and are actually active and visible on the site """
        qs = get_user_model().objects.filter(id__in=self.invited_pendings)
        qs = filter_active_users(qs)
        return qs

    def clear_member_cache(self):
        self.membership_class.clear_member_cache_for_group(self)

    def _clear_local_cache(self):
        """ Stub, called when memberships change """
        pass