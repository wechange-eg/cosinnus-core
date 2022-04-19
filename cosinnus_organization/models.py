# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from collections import OrderedDict
import locale
import six

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Q
from django.urls import reverse
from django.db import models
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from osm_field.fields import OSMField, LatitudeField, LongitudeField

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus.models import BaseMembership, MEMBER_STATUS, MembersManagerMixin, MEMBERSHIP_ADMIN, MEMBERSHIP_STATUSES, \
    MEMBERSHIP_PENDING, MEMBERSHIP_MEMBER, MEMBERSHIP_INVITED_PENDING
from cosinnus.utils.files import image_thumbnail_url, \
    image_thumbnail, get_organization_avatar_filename, get_organization_wallpaper_filename, get_image_url_for_icon
from cosinnus.utils.functions import clean_single_line_text, \
    unique_aware_slugify, sort_key_strcoll_attr
from cosinnus.utils.urls import get_domain_for_portal
from cosinnus.models.mixins.indexes import IndexingUtilsMixin
from phonenumber_field.modelfields import PhoneNumberField

# this reads the environment and inits the right locale
try:
    locale.setlocale(locale.LC_ALL, ("de_DE", "utf8"))
except:
    locale.setlocale(locale.LC_ALL, "")


class CosinnusOrganizationQS(models.query.QuerySet):
    pass


class OrganizationManager(models.Manager):
    
    # main slug to object key
    _ORGANIZATIONS_SLUG_CACHE_KEY = 'cosinnus/core/portal/%d/organization/slug/%s' # portal_id, slug -> organization
    # (pk -> slug) dict
    _ORGANIZATIONS_PK_TO_SLUG_CACHE_KEY = 'cosinnus/core/portal/%d/organization/pks' # portal_id -> {(pk, slug), ...} 
    
    def get_cached(self, slugs=None, pks=None, select_related_media_tag=True, portal_id=None):
        """
        Gets all organizations defined by either `slugs` or `pks`.

        `slugs` and `pks` may be a list or tuple of identifiers to use for
        request where the elements are of type string / unicode or int,
        respectively. You may provide a single string / unicode or int directly
        to query only one object.

        :returns: An instance or a list of instances of :class:`CosinnusGroup`.
        :raises: If a single object is defined a `CosinnusGroup.DoesNotExist`
            will be raised in case the requested object does not exist.
        """
        if portal_id is None:
            portal_id = CosinnusPortal.get_current().id
            
        # Check that at most one of slugs and pks is set
        assert not (slugs and pks)
        assert not (slugs or pks)
            
        if slugs is not None:
            if isinstance(slugs, six.string_types):
                # We request a single organization
                slugs = [slugs]
                
            # We request multiple organizations by slugs
            keys = [self._ORGANIZATIONS_SLUG_CACHE_KEY % (portal_id, s) for s in slugs]
            organizations = cache.get_many(keys)
            missing = [key.split('/')[-1] for key in keys if key not in organizations]
            if missing:
                # we can only find organizations via this function that are in the same portal we run in
                query = self.get_queryset().filter(portal__id=portal_id, is_active=True, slug__in=missing)
                if select_related_media_tag:
                    query = query.select_related('media_tag')
                
                for organization in query:
                    organizations[self._ORGANIZATIONS_SLUG_CACHE_KEY % (portal_id, organization.slug)] = organization
                cache.set_many(organizations, settings.COSINNUS_ORGANIZATION_CACHE_TIMEOUT)
            
            # sort by a good sorting function that acknowldges umlauts, etc, case insensitive
            organization_list = list(organizations.values())
            organization_list = sorted(organization_list, key=sort_key_strcoll_attr('name'))
            return organization_list
            
        elif pks is not None:
            if isinstance(pks, int):
                pks = [pks]
            else:
                # We request multiple organizations
                cached_pks = self.get_pks(portal_id=portal_id)
                slugs = [_f for _f in (cached_pks.get(pk, []) for pk in pks) if _f]
                if slugs:
                    return self.get_cached(slugs=slugs, portal_id=portal_id)
                return []  # We rely on the slug and id maps being up to date
        return []
    
    
    def get_pks(self, portal_id=None, force=True):
        """
        Gets the (pks -> slug) :class:`OrderedDict` from the cache or, if the can has not been filled,
        gets the pks and slugs from the database and fills the cache.
        
        @param force: if True, forces a rebuild of the pk and slug cache for this group type
        :returns: A :class:`OrderedDict` with a `pk => slug` mapping of all
            groups
        """
        if portal_id is None:
            portal_id = CosinnusPortal.get_current().id
            
        pks = cache.get(self._ORGANIZATIONS_PK_TO_SLUG_CACHE_KEY % (portal_id))
        if force or pks is None:
            # we can only find groups via this function that are in the same portal we run in
            pks = OrderedDict(self.filter(portal__id=portal_id, is_active=True).values_list('id', 'slug').all())
            cache.set(self._ORGANIZATIONS_PK_TO_SLUG_CACHE_KEY % (portal_id), pks,
                settings.COSINNUS_ORGANIZATION_CACHE_TIMEOUT)
        return pks
    
    def all_in_portal(self):
        """ Returns all groups within the current portal only """
        return self.active().filter(portal=CosinnusPortal.get_current())
    
    def public(self):
        """ Returns active, public Organizations """
        qs = self.active()
        return qs.filter(media_tag__public=True)
    
    def active(self):
        """ Returns active Organizations """
        qs = self.get_queryset()
        return qs.filter(is_active=True)
    
    def get_by_shortid(self, shortid):
        """ Gets an organization from a string id in the form of `"%(portal)d.%(type)s.%(slug)s"`. 
            Returns None if not found. """
        portal, __, slug = shortid.split('.')
        portal = int(portal)
        try:
            qs = self.get_queryset().filter(portal_id=portal, slug=slug)
            return qs[0]
        except self.model.DoesNotExist:
            return None
    
    def get_queryset(self):
        return CosinnusOrganizationQS(self.model, using=self._db).select_related('portal')

    def get_for_user_pks(self, user, include_public=False, member_status_in=MEMBER_STATUS, includeInactive=False):
        """
        :returns: a list of primary keys to :class:`CosinnusOrganization` the given
            user is a member or admin of, and not a pending member!.
        """
        qs = self.get_queryset()
        if not includeInactive:
            qs = qs.filter(is_active=True)
        if include_public:
            return qs.filter(Q(public__exact=True) | Q(memberships__user_id=user.pk) & Q(memberships__status__in=member_status_in)) \
                .values_list('id', flat=True).distinct()
        return qs.filter(Q(memberships__user_id=user.pk) & Q(memberships__status__in=member_status_in)) \
            .values_list('id', flat=True).distinct()

    def get_for_user_group_admin_pks(self, user, include_public=False, member_status_in=MEMBER_STATUS, includeInactive=False):
        """
        :returns: a list of primary keys to :class:`CosinnusOrganization` the given
            user is an admin of, and not a pending member!.
        """
        return self.get_for_user_pks(user, include_public, member_status_in=[MEMBERSHIP_ADMIN, ], includeInactive=includeInactive)


class CosinnusOrganizationMembership(BaseMembership):
    group = models.ForeignKey('cosinnus_organization.CosinnusOrganization', related_name='memberships', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='organization_memberships',
                             on_delete=models.CASCADE)

    CACHE_KEY_MODEL = 'CosinnusOrganization'

    class Meta(BaseMembership.Meta):
        app_label = 'cosinnus_organization'
        verbose_name = _('Organization membership')
        verbose_name_plural = _('Organization memberships')

    def __str__(self):
        return "<user: %(user)s, group: %(group)s, status: %(status)d>" % {
            'user': getattr(self, 'user', None),
            'group': getattr(self, 'group', None),
            'status': self.status,
        }

    def __init__(self, *args, **kwargs):
        super(CosinnusOrganizationMembership, self).__init__(*args, **kwargs)
        self._status = self.status


class CosinnusUnregisteredUserOrganizationInvite(BaseMembership):
    """ A placeholder for an organizations invite of person's who has been invited via email to join.
        Used to imprint a real `CosinnusOrganizationMembership` once that user registers.
        The ``status`` field is ignored because it would always be on pending anyways. """

    group = models.ForeignKey('cosinnus_organization.CosinnusOrganization', related_name='unregistered_user_invites',
                              on_delete=models.CASCADE)
    email = models.EmailField(_('email address'))
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                   related_name='cosinnus_organization_invitations', on_delete=models.SET_NULL)
    last_modified = models.DateTimeField(_('Last modified'), auto_now=True, editable=False)

    CACHE_KEY_MODEL = 'CosinnusUnregisteredUserOrganizationInvite'

    class Meta(object):
        app_label = 'cosinnus_organization'
        verbose_name = _('Organization Invite for Unregistered User')
        verbose_name_plural = _('Organization Invites for Unregistered Users')
        unique_together = (('email', 'group'),)


@six.python_2_unicode_compatible
class CosinnusOrganization(IndexingUtilsMixin, MembersManagerMixin, models.Model):
    """
    Organization model.
    """
    TYPE_OTHER = 0
    TYPE_CIVIL_SOCIETY_ORGANIZATION = 1
    TYPE_COMPANY = 2
    TYPE_PUBLIC_INSTITUTION = 3
    TYPE_CHOICES = (
        (TYPE_CIVIL_SOCIETY_ORGANIZATION, _('Civil society organization')),
        (TYPE_COMPANY, _('Company (commercial)')),
        (TYPE_PUBLIC_INSTITUTION, _('Public institution')),
        (TYPE_OTHER, _('Other')),
    )

    portal = models.ForeignKey(CosinnusPortal, verbose_name=_('Portal'), related_name='organizations',
        null=False, blank=False, default=1, on_delete=models.CASCADE) # port_id 1 is created in a datamigration!
    
    name = models.CharField(_('Name of the organization'), max_length=250)  # removed validators=[group_name_validator])
    slug = models.SlugField(_('Slug'), 
        help_text=_('Be extremely careful when changing this slug manually! There can be many side-effects (redirects breaking e.g.)!'), 
        max_length=50)
    type = models.PositiveSmallIntegerField(_('Organization type'), blank=False, choices=TYPE_CHOICES)
    type_other = models.CharField(_('Organization type'), max_length=255, blank=True)
    description = models.TextField(verbose_name=_('Short Description'),
         help_text=_('Short Description. Internal, will not be shown publicly.'), blank=True)
    avatar = models.ImageField(_("Logo"), null=True, blank=True,
        upload_to=get_organization_avatar_filename,
        max_length=250)
    wallpaper = models.ImageField(_("Wallpaper image"),
        help_text=_('Shown as large banner image on the Microsite (1140 x 240 px)'),
        null=True, blank=True,
        upload_to=get_organization_wallpaper_filename,
        max_length=250)
    website = models.URLField(_('Website'), max_length=100, blank=True, null=True)
    email = models.EmailField(_('Email Address'), null=True, blank=True)
    phone_number = PhoneNumberField(('Phone Number'), blank=True, null=True)

    media_tag = models.OneToOneField(settings.COSINNUS_TAG_OBJECT_MODEL,
        blank=True, null=True, editable=False, on_delete=models.SET_NULL)
    is_active = models.BooleanField(_('Is active'),
        help_text='If an organization is not active, it counts as non-existent for all purposes and views on the website.',
        default=True)
    created = models.DateTimeField(verbose_name=_('Created'), editable=False, auto_now_add=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL,
        verbose_name=_('Creator'),
        on_delete=models.CASCADE,
        null=True,
        related_name='organizations')
    last_modified = models.DateTimeField(
        verbose_name=_('Last modified'),
        editable=False,
        auto_now=True)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True,
                                   related_name='cosinnus_organizations', through=CosinnusOrganizationMembership)

    settings = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)
    extra_fields = models.JSONField(default=dict, blank=True, encoder=DjangoJSONEncoder)
    objects = OrganizationManager()

    # this indicates that objects of this model are in some way always visible by registered users
    # on the platform, no matter their visibility settings, and thus subject to moderation
    cosinnus_always_visible_by_users_moderator_flag = True
    # Required for require_read_access check
    public = True
    membership_class = CosinnusOrganizationMembership
    
    class Meta(object):
        ordering = ('created',)
        verbose_name = _('Cosinnus Organization')
        verbose_name_plural = _('Cosinnus Organizations')
        unique_together = ('slug', 'portal', )

    def __init__(self, *args, **kwargs):
        super(CosinnusOrganization, self).__init__(*args, **kwargs)
        self._portal_id = self.portal_id
        self._slug = self.slug

    def __str__(self):
        return '%s (Portal %d)' % (self.name, self.portal_id)
    
    def save(self, *args, **kwargs):
        created = bool(self.pk is None)
        slugs = [self.slug] if self.slug else []
        self.name = clean_single_line_text(self.name)
        
        current_portal = self.portal or CosinnusPortal.get_current()
        unique_aware_slugify(self, 'name', 'slug', portal_id=current_portal)
        
        if not self.slug:
            raise ValidationError(_('Slug must not be empty.'))
        slugs.append(self.slug)
        # sanity check for missing media_tag:
        if not self.media_tag:
            from cosinnus.models.tagged import get_tag_object_model
            media_tag = get_tag_object_model()._default_manager.create()
            self.media_tag = media_tag

        # FIXME: This shouldn't be necessary, but throws an error if missing
        self.media_tag.save()
        
        # set portal to current
        if created and not self.portal:
            self.portal = CosinnusPortal.get_current()
            
        super(CosinnusOrganization, self).save(*args, **kwargs)
        
        self._clear_cache(slugs=slugs)
        # force rebuild the pk --> slug cache. otherwise when we query that, this group might not be in it
        self.__class__.objects.get_pks(force=True)
        
        self._portal_id = self.portal_id
        self._slug = self.slug

    def delete(self, *args, **kwargs):
        self._clear_cache(slug=self.slug)
        super(CosinnusOrganization, self).delete(*args, **kwargs)
        
    @classmethod
    def _clear_cache(self, slug=None, slugs=None):
        slugs = set([s for s in slugs]) if slugs else set()
        if slug: slugs.add(slug)
        keys = [
            self.objects._ORGANIZATIONS_PK_TO_SLUG_CACHE_KEY % (CosinnusPortal.get_current().id),
        ]
        if slugs:
            keys.extend([self.objects._ORGANIZATIONS_SLUG_CACHE_KEY % (CosinnusPortal.get_current().id, s) for s in slugs])
        cache.delete_many(keys)
        
    def clear_cache(self):
        self._clear_cache(slug=self.slug)

    def get_type(self):
        if self.type == self.TYPE_OTHER:
            return self.type_other
        else:
            return self.get_type_display()

    @property
    def image_url(self):
        return self.image.url if self.image else None
    
    def get_image_thumbnail(self, size=(500, 275)):
        return image_thumbnail(self.image, size)

    def get_image_thumbnail_url(self, size=(500, 275)):
        return image_thumbnail_url(self.image, size)

    def get_icon(self):
        """ Returns the font-awesome icon"""
        return 'fa-building'

    def get_image_field_for_icon(self):
        return self.avatar or get_image_url_for_icon(self.get_icon(), large=True)

    def get_image_field_for_background(self):
        return self.wallpaper

    @property
    def avatar_url(self):
        return self.avatar.url if self.avatar else None

    def get_avatar_thumbnail(self, size=(80, 80)):
        return image_thumbnail(self.avatar, size)

    def get_avatar_thumbnail_url(self, size=(80, 80)):
        return image_thumbnail_url(self.avatar, size) or get_image_url_for_icon(self.get_icon(), large=True)

    def is_foreign_portal(self):
        return CosinnusPortal.get_current().id != self.portal_id
    
    def media_tag_object(self):
        key = '_media_tag_cache'
        if not hasattr(self, key):
            setattr(self, key, self.media_tag)
        return getattr(self, key)
    
    def get_absolute_url(self):
        return get_domain_for_portal(self.portal) + reverse('cosinnus:organization-detail',
                                                            kwargs={'organization': self.slug})
    
    def get_edit_url(self):
        return reverse('cosinnus:organization-edit', kwargs={'organization': self.slug})
    
    def get_delete_url(self):
        return reverse('cosinnus:organization-delete', kwargs={'organization': self.slug})


class CosinnusOrganizationSocialMedia(models.Model):
    url = models.URLField(_('URL'), max_length=100)

    organization = models.ForeignKey(
        CosinnusOrganization,
        verbose_name=_('Organization'),
        on_delete=models.CASCADE,
        related_name='social_media',
    )

    class Meta(object):
        verbose_name = _('CosinnusOrganizationSocialMedia')
        verbose_name_plural = _('CosinnusOrganizationSocialMedia')

    @property
    def icon(self):
        """Guess font awesome icon from URL"""
        url = self.url.lower()
        if 'facebook' in url:
            return 'facebook'
        elif 'twitter' in url:
            return 'twitter'
        elif 'instagram' in url:
            return 'instagram'
        elif 'linkedin' in url:
            return 'linkedin'
        elif 'xing' in url:
            return 'xing'
        elif 'youtube' in url:
            return 'youtube'
        elif 'vimeo' in url:
            return 'vimeo'
        elif 'google' in url:
            return 'google'
        else:
            return 'external-link'


class CosinnusOrganizationLocation(models.Model):
    location = OSMField(_('Location'), blank=True, null=True)
    location_lat = LatitudeField(_('Latitude'), blank=True, null=True)
    location_lon = LongitudeField(_('Longitude'), blank=True, null=True)

    organization = models.ForeignKey(
        CosinnusOrganization,
        verbose_name=_('Organization'),
        on_delete=models.CASCADE,
        related_name='locations',
    )

    class Meta(object):
        verbose_name = _('CosinnusOrganizationLocation')
        verbose_name_plural = _('CosinnusOrganizationLocations')

    @property
    def location_url(self):
        if not self.location_lat or not self.location_lon:
            return None
        return 'https://openstreetmap.org/?mlat=%s&mlon=%s&zoom=15&layers=M' % (self.location_lat, self.location_lon)


class CosinnusOrganizationGroupQuerySet(models.QuerySet):

    def active_groups(self):
        return self.filter(status__in=MEMBER_STATUS, group__is_active=True)

    def active_organizations(self):
        return self.filter(status__in=MEMBER_STATUS, organization__is_active=True)


class CosinnusOrganizationGroup(models.Model):
    organization = models.ForeignKey('cosinnus_organization.CosinnusOrganization', related_name='groups', on_delete=models.CASCADE)
    group = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL, related_name='organizations', on_delete=models.CASCADE)
    status = models.PositiveSmallIntegerField(choices=MEMBERSHIP_STATUSES, db_index=True, default=MEMBERSHIP_PENDING)
    date = models.DateTimeField(auto_now_add=True, editable=False)

    objects = CosinnusOrganizationGroupQuerySet.as_manager()

    class Meta:
        verbose_name = _('Organization group')
        verbose_name_plural = _('Organization groups')
        unique_together = (('organization', 'group'),)

    def __init__(self, *args, **kwargs):
        super(CosinnusOrganizationGroup, self).__init__(*args, **kwargs)
        self._old_current_status = self.status

    def __str__(self):
        return "<organization: %(organization)s, group: %(group)s, status: %(status)d>" % {
            'organization': getattr(self, 'organization', None),
            'group': getattr(self, 'group', None),
            'status': self.status,
        }

    def save(self, *args, **kwargs):
        # Only update the date if the the state changes from pending to member
        # or admin
        if (self._old_current_status == MEMBERSHIP_PENDING or self._old_current_status == MEMBERSHIP_INVITED_PENDING) and \
                (self.status in MEMBER_STATUS):
            self.date = now()
        return super(CosinnusOrganizationGroup, self).save(*args, **kwargs)
