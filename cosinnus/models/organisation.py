# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import OrderedDict
import re
import six

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _, pgettext_lazy as p_

from tinymce.models import HTMLField

from cosinnus.conf import settings
from cosinnus.utils.functions import unique_aware_slugify
from cosinnus.utils.files import get_organisation_avatar_filename
from django.core.urlresolvers import reverse


#: Role defining a user has requested to be added to a organisation
ORGANISATION_MEMBERSHIP_PENDING = 0

#: Role defining a user is a member but not an admin of a organisation
ORGANISATION_MEMBERSHIP_MEMBER = 1

#: Role defining a user is an admin of a organisation
ORGANISATION_MEMBERSHIP_ADMIN = 2

ORGANISATION_MEMBERSHIP_STATUSES = (
    (ORGANISATION_MEMBERSHIP_PENDING, p_('cosinnus membership status', 'pending')),
    (ORGANISATION_MEMBERSHIP_MEMBER, p_('cosinnus membership status', 'member')),
    (ORGANISATION_MEMBERSHIP_ADMIN, p_('cosinnus membership status', 'admin')),
)

#: A user is a member of a organisation if either is an explicit member or admin
ORGANISATION_MEMBER_STATUS = (ORGANISATION_MEMBERSHIP_MEMBER, ORGANISATION_MEMBERSHIP_ADMIN,)


_ORGANISATION_SLUG_CACHE_KEY = 'cosinnus/core/organisation/slugs'
_ORGANISATION_PK_CACHE_KEY = 'cosinnus/core/organisation/pks'
_ORGANISATION_CACHE_KEY = 'cosinnus/core/organisation/%s'

_ORGANISATION_MEMBERSHIP_ADMINS_KEY = 'cosinnus/core/organisation_membership/admins/%d'
_ORGANISATION_MEMBERSHIP_MEMBERS_KEY = 'cosinnus/core/organisation_membership/members/%d'
_ORGANISATION_MEMBERSHIP_PENDINGS_KEY = 'cosinnus/core/organisation_membership/pendings/%d'


def organisation_name_validator(value):
    RegexValidator(
        re.compile('^[^/]+$'),
        _('Enter a valid organisation name. Forward slash is not allowed.'),
        'invalid'
    )(value)


class CosinnusOrganisationQS(models.query.QuerySet):

    def filter_membership_status(self, status):
        if isinstance(status, (list, tuple)):
            return self.filter(memberships__status__in=status)
        return self.filter(memberships__status=status)

    def update(self, **kwargs):
        ret = super(CosinnusOrganisationQS, self).update(**kwargs)
        self.model._clear_cache()
        return ret


class CosinnusOrganisationMembershipQS(models.query.QuerySet):

    def filter_membership_status(self, status):
        if isinstance(status, (list, tuple)):
            return self.filter(status__in=status)
        return self.filter(status=status)

    def update(self, **kwargs):
        ret = super(CosinnusOrganisationMembershipQS, self).update(**kwargs)
        self.model._clear_cache()
        return ret


class CosinnusOrganisationManager(models.Manager):

    use_for_related_fields = True

    def get_queryset(self):
        return CosinnusOrganisationQS(self.model, using=self._db)

    get_query_set = get_queryset

    def filter_membership_status(self, status):
        return self.get_queryset().filter_membership_status(status)

    def get_slugs(self):
        """
        Gets all organisation slugs from the cache or, if the can has not been filled,
        gets the slugs and pks from the database and fills the cache.

        :returns: A :class:`OrderedDict` with a `slug => pk` mapping of all
            organisations
        """
        slugs = cache.get(_ORGANISATION_SLUG_CACHE_KEY)
        if slugs is None:
            slugs = OrderedDict(self.values_list('slug', 'id').all())
            pks = OrderedDict((v, k) for k, v in six.iteritems(slugs))
            cache.set(_ORGANISATION_SLUG_CACHE_KEY, slugs,
                settings.COSINNUS_ORGANISATION_CACHE_TIMEOUT)
            cache.set(_ORGANISATION_PK_CACHE_KEY, pks,
                settings.COSINNUS_ORGANISATION_CACHE_TIMEOUT)
        return slugs

    def get_pks(self):
        """
        Gets all organisation pks from the cache or, if the can has not been filled,
        gets the pks and slugs from the database and fills the cache.

        :returns: A :class:`OrderedDict` with a `pk => slug` mapping of all
            organisations
        """
        pks = cache.get(_ORGANISATION_PK_CACHE_KEY)
        if pks is None:
            pks = OrderedDict(self.values_list('id', 'slug').all())
            slugs = OrderedDict((v, k) for k, v in six.iteritems(pks))
            cache.set(_ORGANISATION_PK_CACHE_KEY, pks,
                settings.COSINNUS_ORGANISATION_CACHE_TIMEOUT)
            cache.set(_ORGANISATION_SLUG_CACHE_KEY, slugs,
                settings.COSINNUS_ORGANISATION_CACHE_TIMEOUT)
        return pks

    def get_cached(self, slugs=None, pks=None):
        """
        Gets all organisations defined by either `slugs` or `pks`.

        `slugs` and `pks` may be a list or tuple of identifiers to use for
        request where the elements are of type string / unicode or int,
        respectively. You may provide a single string / unicode or int directly
        to query only one object.

        :returns: An instance or a list of instances of :class:`CosinnusOrganisation`.
        :raises: If a single object is defined a `CosinnusOrganisation.DoesNotExist`
            will be raised in case the requested object does not exist.
        """
        # Check that at most one of slugs and pks is set
        assert not (slugs and pks)
        if (slugs is None) and (pks is None):
            slugs = list(self.get_slugs().keys())

        if slugs is not None:
            if isinstance(slugs, six.string_types):
                # We request a single organisation
                slug = slugs
                organisation = cache.get(_ORGANISATION_CACHE_KEY % slug)
                if organisation is None:
                    organisation = super(CosinnusOrganisationManager, self).get(slug=slug)
                    cache.set(_ORGANISATION_CACHE_KEY % organisation.slug, organisation,
                        settings.COSINNUS_ORGANISATION_CACHE_TIMEOUT)
                return organisation
            else:
                # We request multiple organisations by slugs
                keys = [_ORGANISATION_CACHE_KEY % s for s in slugs]
                organisations = cache.get_many(keys)
                missing = [key.split('/')[-1] for key in keys if key not in organisations]
                if missing:
                    query = self.get_queryset().filter(slug__in=missing)
                    for organisation in query:
                        organisations[_ORGANISATION_CACHE_KEY % organisation.slug] = organisation
                    cache.set_many(organisations, settings.COSINNUS_ORGANISATION_CACHE_TIMEOUT)
                return sorted(organisations.values(), key=lambda x: x.name)
        elif pks is not None:
            if isinstance(pks, int):
                # We request a single organisation
                cached_pks = self.get_pks()
                slug = cached_pks.get(pks, None)
                if slug:
                    return self.get_cached(slugs=slug)
                return None  # We rely on the slug and id maps being up to date
            else:
                # We request multiple organisations
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
        :returns: a list of :class:`CosinnusOrganisation` the given user is a member
            or admin of.
        """
        return self.get_cached(pks=self.get_for_user_pks(user))

    def get_for_user_pks(self, user):
        """
        :returns: a list of primary keys to :class:`CosinnusOrganisation` the given
            user is a member or admin of, and not a pending member!.
        """
        return self.filter(Q(memberships__user_id=user.pk) & Q(memberships__status__in=ORGANISATION_MEMBER_STATUS)) \
            .values_list('id', flat=True).distinct()
        
    def public(self):
        """
        :returns: An iterator over all public organisations.
        """
        for organisation in self.get_cached():
            if organisation.public:
                yield organisation


class CosinnusOrganisationMembershipManager(models.Manager):

    use_for_related_fields = True

    def get_queryset(self):
        return CosinnusOrganisationMembershipQS(self.model, using=self._db)

    get_query_set = get_queryset

    def filter_membership_status(self, status):
        return self.get_queryset().filter_membership_status(status)

    def _get_users_for_single_organisation(self, organisation_id, cache_key, status):
        uids = cache.get(cache_key % organisation_id)
        if uids is None:
            query = self.filter(organisation_id=organisation_id).filter_membership_status(status)
            uids = list(query.values_list('user_id', flat=True).all())
            cache.set(cache_key % organisation_id, uids)
        return uids

    def _get_users_for_multiple_organisations(self, organisation_ids, cache_key, status):
        keys = [cache_key % g for g in organisation_ids]
        users = cache.get_many(keys)
        missing = list(map(int, (key.split('/')[-1] for key in keys if key not in users)))
        if missing:
            _q = self.filter_membership_status(status).values_list('user_id', flat=True)
            for organisation in missing:
                uids = list(_q._clone().filter(organisation_id=organisation).all())
                users[cache_key % organisation] = uids
            cache.set_many(users)
        return {int(k.split('/')[-1]): v for k, v in six.iteritems(users)}

    def get_admins(self, organisation=None, organisations=None):
        """
        Given either a organisation or a list of organisations, this function returns all
        members with the :data:`ORGANISATION_MEMBERSHIP_ADMIN` role.
        """
        assert (organisation is None) ^ (organisations is None)
        if organisation:
            gid = isinstance(organisation, int) and organisation or organisation.pk
            return self._get_users_for_single_organisation(gid, _ORGANISATION_MEMBERSHIP_ADMINS_KEY, ORGANISATION_MEMBERSHIP_ADMIN)
        else:
            gids = [isinstance(g, int) and g or g.pk for g in organisations]
            return self._get_users_for_multiple_organisations(gids, _ORGANISATION_MEMBERSHIP_ADMINS_KEY, ORGANISATION_MEMBERSHIP_ADMIN)

    def get_members(self, organisation=None, organisations=None):
        """
        Given either a organisation or a list of organisations, this function returns all
        members with the :data:`ORGANISATION_MEMBERSHIP_MEMBER` OR `ORGANISATION_MEMBERSHIP_ADMIN` role.
        """
        assert (organisation is None) ^ (organisations is None)
        if organisation:
            gid = isinstance(organisation, int) and organisation or organisation.pk
            return self._get_users_for_single_organisation(gid, _ORGANISATION_MEMBERSHIP_MEMBERS_KEY, ORGANISATION_MEMBER_STATUS)
        else:
            gids = [isinstance(g, int) and g or g.pk for g in organisations]
            return self._get_users_for_multiple_organisations(gids, _ORGANISATION_MEMBERSHIP_MEMBERS_KEY, ORGANISATION_MEMBER_STATUS)

    def get_pendings(self, organisation=None, organisations=None):
        """
        Given either a organisation or a list of organisations, this function returns all
        members with the :data:`ORGANISATION_MEMBERSHIP_PENDING` role.
        """
        assert (organisation is None) ^ (organisations is None)
        if organisation:
            gid = isinstance(organisation, int) and organisation or organisation.pk
            return self._get_users_for_single_organisation(gid, _ORGANISATION_MEMBERSHIP_PENDINGS_KEY, ORGANISATION_MEMBERSHIP_PENDING)
        else:
            gids = [isinstance(g, int) and g or g.pk for g in organisations]
            return self._get_users_for_multiple_organisations(gids, _ORGANISATION_MEMBERSHIP_PENDINGS_KEY, ORGANISATION_MEMBERSHIP_PENDING)


@python_2_unicode_compatible
class CosinnusOrganisation(models.Model):
    name = models.CharField(_('Name'), max_length=100,
        validators=[organisation_name_validator])
    slug = models.SlugField(_('Slug'), max_length=50, unique=True, blank=True)
    description = HTMLField(verbose_name=_('Description'), blank=True)
    avatar = models.ImageField(_("Avatar"), null=True, blank=True,
        upload_to=get_organisation_avatar_filename)
    public = models.BooleanField(_('Public'), default=False)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True,
        related_name='cosinnus_organisations', through='CosinnusOrganisationMembership')
    media_tag = models.OneToOneField(settings.COSINNUS_TAG_OBJECT_MODEL,
        blank=True, null=True, editable=False, on_delete=models.PROTECT)
    
    objects = CosinnusOrganisationManager()

    class Meta:
        app_label = 'cosinnus'
        ordering = ('name',)
        verbose_name = _('Cosinnus organisation')
        verbose_name_plural = _('Cosinnus organisations')

    def __init__(self, *args, **kwargs):
        super(CosinnusOrganisation, self).__init__(*args, **kwargs)
        self._admins = None
        self._members = None
        self._pendings = None

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        super(CosinnusOrganisation, self).delete(*args, **kwargs)
        self._clear_cache()

    def save(self, *args, **kwargs):
        slugs = [self.slug] if self.slug else []
        unique_aware_slugify(self, 'name', 'slug')
        if not self.slug:
            raise ValidationError(_('Slug must not be empty.'))
        # sanity check for missing media_tag:
        if not self.media_tag:
            from cosinnus.models.tagged import get_tag_object_model
            media_tag = get_tag_object_model()._default_manager.create()
            self.media_tag = media_tag
        super(CosinnusOrganisation, self).save(*args, **kwargs)
        slugs.append(self.slug)
        self._clear_cache(slug=self.slug)

    @property
    def admins(self):
        if self._admins is None:
            self._admins = CosinnusOrganisationMembership.objects.get_admins(self.pk)
        return self._admins

    def is_admin(self, user):
        """Checks whether the given user is an admin of this organisation"""
        uid = isinstance(user, int) and user or user.pk
        return uid in self.admins

    @property
    def members(self):
        if self._members is None:
            self._members = CosinnusOrganisationMembership.objects.get_members(self.pk)
        return self._members

    def is_member(self, user):
        """Checks whether the given user is a member of this organisation"""
        uid = isinstance(user, int) and user or user.pk
        return uid in self.members

    @property
    def pendings(self):
        if self._pendings is None:
            self._pendings = CosinnusOrganisationMembership.objects.get_pendings(self.pk)
        return self._pendings

    def is_pending(self, user):
        """Checks whether the given user has a pending status on this organisation"""
        uid = isinstance(user, int) and user or user.pk
        return uid in self.pendings

    @classmethod
    def _clear_cache(self, slug=None, slugs=None):
        keys = [
            _ORGANISATION_SLUG_CACHE_KEY,
            _ORGANISATION_PK_CACHE_KEY,
        ]
        if slug:
            keys.append(_ORGANISATION_CACHE_KEY % slug)
        if slugs:
            keys.extend([_ORGANISATION_CACHE_KEY % s for s in slugs])
        cache.delete_many(keys)
        if isinstance(self, CosinnusOrganisation):
            self._clear_local_cache()

    def _clear_local_cache(self):
        self._admins = self._members = self._pendings = None
        
    @property
    def avatar_url(self):
        return self.avatar.url if self.avatar else None
    
    def media_tag_object(self):
        key = '_media_tag_cache'
        if not hasattr(self, key):
            setattr(self, key, self.media_tag)
        return getattr(self, key)
    
    def get_absolute_url(self):
        return reverse('cosinnus:organisation-dashboard', kwargs={'organisation': self.slug})


@python_2_unicode_compatible
class CosinnusOrganisationMembership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
        related_name='cosinnus_memberships', on_delete=models.CASCADE)
    organisation = models.ForeignKey(CosinnusOrganisation, related_name='memberships',
        on_delete=models.CASCADE)
    status = models.PositiveSmallIntegerField(choices=ORGANISATION_MEMBERSHIP_STATUSES,
        db_index=True, default=ORGANISATION_MEMBERSHIP_PENDING)
    date = models.DateTimeField(auto_now_add=True, editable=False)

    objects = CosinnusOrganisationMembershipManager()

    class Meta:
        app_label = 'cosinnus'
        unique_together = (('user', 'organisation'),)
        verbose_name = _('Organisation membership')
        verbose_name_plural = _('Organisation memberships')

    def __init__(self, *args, **kwargs):
        super(CosinnusOrganisationMembership, self).__init__(*args, **kwargs)
        self._old_current_status = self.status

    def __str__(self):
        return "<user: %(user)s, organisation: %(organisation)s, status: %(status)d>" % {
            'user': self.user,
            'organisation': self.organisation,
            'status': self.status,
        }

    def delete(self, *args, **kwargs):
        super(CosinnusOrganisationMembership, self).delete(*args, **kwargs)
        self._clear_cache()

    def save(self, *args, **kwargs):
        # Only update the date if the the state changes from pending to member
        # or admin
        if self._old_current_status == ORGANISATION_MEMBERSHIP_PENDING and \
                self.status != self._old_current_status:
            self.date = now()
        super(CosinnusOrganisationMembership, self).save(*args, **kwargs)
        self._clear_cache()

    def _clear_cache(self):
        cache.delete_many([
            _ORGANISATION_MEMBERSHIP_ADMINS_KEY % self.organisation.pk,
            _ORGANISATION_MEMBERSHIP_MEMBERS_KEY % self.organisation.pk,
            _ORGANISATION_MEMBERSHIP_PENDINGS_KEY % self.organisation.pk,
        ])
        self.organisation._clear_local_cache()
