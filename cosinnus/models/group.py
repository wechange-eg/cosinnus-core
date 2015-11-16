# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import OrderedDict
import os
import re
import six

from django.contrib.sites.models import Site
from django.core.cache import cache
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.core.validators import RegexValidator, MaxLengthValidator
from django.db import models
from django.db.models import Q
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _, pgettext_lazy as p_

from taggit.managers import TaggableManager
from tinymce.models import HTMLField

from cosinnus.conf import settings
from cosinnus.models.cms import CosinnusMicropage
from cosinnus.utils.functions import unique_aware_slugify,\
    clean_single_line_text
from cosinnus.utils.files import get_group_avatar_filename,\
    get_portal_background_image_filename, get_group_wallpaper_filename,\
    get_cosinnus_media_file_folder
from django.core.urlresolvers import reverse
from django.utils.functional import cached_property
from cosinnus.utils.urls import group_aware_reverse, get_domain_for_portal
from cosinnus.utils.compat import atomic
from cosinnus.core import signals
from cosinnus.core.registries.group_models import group_model_registry
from django.db.models.signals import post_delete, post_save
from django.dispatch.dispatcher import receiver
from django.template.loader import render_to_string

from django.db import IntegrityError
from django.contrib import messages

import logging
import shutil
from easy_thumbnails.files import get_thumbnailer
from easy_thumbnails.exceptions import InvalidImageFormatError

logger = logging.getLogger('cosinnus')

# this reads the environment and inits the right locale
import locale
try:
    locale.setlocale(locale.LC_ALL, ("de_DE", "utf8"))
except:
    locale.setlocale(locale.LC_ALL, "")
    

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

_MEMBERSHIP_ADMINS_KEY = 'cosinnus/core/membership/%s/admins/%d'
_MEMBERSHIP_MEMBERS_KEY = 'cosinnus/core/membership/%s/members/%d'
_MEMBERSHIP_PENDINGS_KEY = 'cosinnus/core/membership/%s/pendings/%d'


def group_name_validator(value):
    RegexValidator(
        re.compile('^[^/]+$'),
        _('Enter a valid name. Forward slash is not allowed.'),
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
    
    """ These caches are the directories of which groups are active and displayed in each portal. 
        They are typed by the Groups' Manager (!) so that one can be sure to always receive the correct Model instantiation.
        This also means that when called on the base CosinnusGroupManager, one will receive cached CosinnusGroups and not
        either CosinnusProject or CosinnusSociety. This works as intended, as often functions wish to explicitly get a set of
        both of these (membership queries, BaseTaggableObject displays in Stream, etc) """
    
    # list of all group slugs and the pk mapped to each slug
    _GROUPS_SLUG_CACHE_KEY = 'cosinnus/core/portal/%d/group/%s/slugs' # portal_id, self.__class__.__name__  --> list ( slug (str), pk (int) )
    # list of all group pks and the slug mapped to each pk
    _GROUPS_PK_CACHE_KEY = 'cosinnus/core/portal/%d/group/%s/pks' # portal_id, self.__class__.__name__   --> list ( pk (int), slug (str) )
    # actual slug to group object cache
    _GROUP_CACHE_KEY = 'cosinnus/core/portal/%d/group/%s/%s' # portal_id, self.__class__.__name__, slug   --> group (obj)
    # group slug to Model type cache, for when only a group slug is known but not the specific CosinnusGroup sub model type
    _GROUP_SLUG_TYPE_CACHE_KEY = 'cosinnus/core/portal/%d/group_slug_type/%s' # portal_id, group_slug  --> type (int)
    # cache for the children ids of a cosinnus group
    _GROUP_CHILDREN_PK_CACHE_KEY = 'cosinnus/core/portal/%d/group_children_pks/%d' # portal_id, pk (int) --> list ( pk (int) )

    use_for_related_fields = True

    def get_queryset(self):
        return CosinnusGroupQS(self.model, using=self._db)

    get_query_set = get_queryset

    def filter_membership_status(self, status):
        return self.get_queryset().filter_membership_status(status)

    def get_slugs(self, portal_id=None):
        """
        Gets all group slugs from the cache or, if the can has not been filled,
        gets the slugs and pks from the database and fills the cache.

        :returns: A :class:`OrderedDict` with a `slug => pk` mapping of all
            groups
        """
        if portal_id is None:
            portal_id = CosinnusPortal.get_current().id
        
        slugs = cache.get(self._GROUPS_SLUG_CACHE_KEY % (portal_id, self.__class__.__name__))
        if slugs is None:
            # we can only find groups via this function that are in the same portal we run in
            slugs = OrderedDict(self.get_queryset().filter(portal_id=portal_id, is_active=True).values_list('slug', 'id').all())
            pks = OrderedDict((v, k) for k, v in six.iteritems(slugs))
            cache.set(self._GROUPS_SLUG_CACHE_KEY % (portal_id, self.__class__.__name__), slugs,
                settings.COSINNUS_GROUP_CACHE_TIMEOUT)
            cache.set(self._GROUPS_PK_CACHE_KEY % (portal_id, self.__class__.__name__), pks,
                settings.COSINNUS_GROUP_CACHE_TIMEOUT)
        return slugs

    def get_pks(self, portal_id=None):
        """
        Gets all group pks from the cache or, if the can has not been filled,
        gets the pks and slugs from the database and fills the cache.

        :returns: A :class:`OrderedDict` with a `pk => slug` mapping of all
            groups
        """
        if portal_id is None:
            portal_id = CosinnusPortal.get_current().id
            
        pks = cache.get(self._GROUPS_PK_CACHE_KEY % (portal_id, self.__class__.__name__))
        if pks is None:
            # we can only find groups via this function that are in the same portal we run in
            pks = OrderedDict(self.filter(portal__id=portal_id, is_active=True).values_list('id', 'slug').all())
            slugs = OrderedDict((v, k) for k, v in six.iteritems(pks))
            cache.set(self._GROUPS_PK_CACHE_KEY % (portal_id, self.__class__.__name__), pks,
                settings.COSINNUS_GROUP_CACHE_TIMEOUT)
            cache.set(self._GROUPS_SLUG_CACHE_KEY % (portal_id, self.__class__.__name__), slugs,
                settings.COSINNUS_GROUP_CACHE_TIMEOUT)
        return pks

    def get_cached(self, slugs=None, pks=None, select_related_media_tag=True, portal_id=None):
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
        if portal_id is None:
            portal_id = CosinnusPortal.get_current().id
            
        # Check that at most one of slugs and pks is set
        assert not (slugs and pks)
        if (slugs is None) and (pks is None):
            slugs = list(self.get_slugs().keys())
            
        if slugs is not None:
            if isinstance(slugs, six.string_types):
                # We request a single group
                slug = slugs
                group = cache.get(self._GROUP_CACHE_KEY % (portal_id, self.__class__.__name__, slug))
                if group is None:
                    # we can only find groups via this function that are in the same portal we run in
                    group = self.get_queryset().filter(portal__id=portal_id, is_active=True).get(slug=slug)
                    cache.set(self._GROUP_CACHE_KEY % (portal_id, self.__class__.__name__, group.slug), group,
                        settings.COSINNUS_GROUP_CACHE_TIMEOUT)
                return group
            else:
                # We request multiple groups by slugs
                keys = [self._GROUP_CACHE_KEY % (portal_id, self.__class__.__name__, s) for s in slugs]
                groups = cache.get_many(keys)
                missing = [key.split('/')[-1] for key in keys if key not in groups]
                if missing:
                    # we can only find groups via this function that are in the same portal we run in
                    query = self.get_queryset().filter(portal__id=portal_id, is_active=True, slug__in=missing)
                    if select_related_media_tag:
                        query = query.select_related('media_tag')
                    
                    for group in query:
                        groups[self._GROUP_CACHE_KEY % (portal_id, self.__class__.__name__, group.slug)] = group
                    cache.set_many(groups, settings.COSINNUS_GROUP_CACHE_TIMEOUT)
                
                # sort by a good sorting function that acknowldges umlauts, etc, case insensitive
                group_list = groups.values()
                group_list.sort(cmp=locale.strcoll, key=lambda x: x.name)
                return group_list
            
        elif pks is not None:
            if isinstance(pks, int):
                # We request a single group
                cached_pks = self.get_pks(portal_id=portal_id)
                slug = cached_pks.get(pks, None)
                if slug:
                    return self.get_cached(slugs=slug, portal_id=portal_id)
                return None  # We rely on the slug and id maps being up to date
            else:
                # We request multiple groups
                cached_pks = self.get_pks(portal_id=portal_id)
                slugs = filter(None, (cached_pks.get(id, []) for id in pks))
                if slugs:
                    return self.get_cached(slugs=slugs, portal_id=portal_id)
                return []  # We rely on the slug and id maps being up to date
        return []
    
    def all_in_portal(self):
        """ Returns all groups within the current portal only """
        return self.get_queryset().filter(portal=CosinnusPortal.get_current(), is_active=True)

    def get(self, slug=None, portal_id=None):
        if portal_id is None:
            portal_id = CosinnusPortal.get_current().id
        return self.get_cached(slugs=slug, portal_id=portal_id)
    
    def get_by_id(self, id=None, portal_id=None):
        if portal_id is None:
            portal_id = CosinnusPortal.get_current().id
        return self.get_cached(pks=id, portal_id=portal_id)
    
    def get_for_user(self, user, includeInactive=False):
        """
        :returns: a list of :class:`CosinnusGroup` the given user is a member
            or admin of.
        """
        return self.get_cached(pks=self.get_for_user_pks(user, includeInactive=includeInactive))

    def get_for_user_pks(self, user, include_public=False, member_status_in=MEMBER_STATUS, includeInactive=False):
        """
        :returns: a list of primary keys to :class:`CosinnusGroup` the given
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
        :returns: a list of primary keys to :class:`CosinnusGroup` the given
            user is an admin of, and not a pending member!.
        """
        return self.get_for_user_pks(user, include_public, member_status_in=[MEMBERSHIP_ADMIN,], includeInactive=includeInactive)
    
    def with_deactivated_app(self, app_name):
        """
        :returns: An iterator over all groups that have a specific cosinnus app deactivated.
        """
        """ also: filter(headline__contains='Lennon')"""
        for group in self.get_cached():
            if group.is_app_deactivated(app_name):
                yield group
    
    def public(self):
        """
        :returns: An iterator over all public groups.
        """
        for group in self.get_cached():
            if group.public:
                yield group


class CosinnusGroupMembershipManager(models.Manager):
    
    """ Note: Thismanager is used for all Groups, and also Portals! """

    use_for_related_fields = True

    def get_queryset(self):
        return CosinnusGroupMembershipQS(self.model, using=self._db)

    get_query_set = get_queryset

    def filter_membership_status(self, status):
        return self.get_queryset().filter_membership_status(status)

    def _get_users_for_single_group(self, group_id, cache_key, status):
        uids = cache.get(cache_key % (self.model.CACHE_KEY_MODEL, group_id))
        if uids is None:
            query = self.filter(group_id=group_id).filter_membership_status(status)
            uids = list(query.values_list('user_id', flat=True).all())
            cache.set(cache_key % (self.model.CACHE_KEY_MODEL, group_id), uids)
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



@python_2_unicode_compatible
class CosinnusPortal(models.Model):
    
    _CURRENT_PORTAL_CACHE_KEY = 'cosinnus/core/portal/current'
    if settings.DEBUG:
        _CUSTOM_CSS_FILENAME = '_ignoreme_cosinnus_custom_portal_%s_styles.css'
    else:
        _CUSTOM_CSS_FILENAME = 'cosinnus_custom_portal_%s_styles.css'
    
    class Meta:
        app_label = 'cosinnus'
        verbose_name = _('Portal')
        verbose_name_plural = _('Portals')
        
    def __init__(self, *args, **kwargs):
        super(CosinnusPortal, self).__init__(*args, **kwargs)
        self._admins = None
        self._members = None
        self._pendings = None
    
    name = models.CharField(_('Name'), max_length=100,
        validators=[group_name_validator])
    slug = models.SlugField(_('Slug'), max_length=50, unique=True, blank=True)
    
    description = HTMLField(verbose_name=_('Description'), blank=True)
    website = models.URLField(_('Website'), max_length=100, blank=True, null=True)
    public = models.BooleanField(_('Public'), default=False)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True,
        related_name='cosinnus_portals', through='CosinnusPortalMembership')
    
    site = models.ForeignKey(Site, unique=True, verbose_name=_('Associated Site'))
    
    protocol = models.CharField(_('Http/Https Protocol (overrides settings)'), max_length=8,
                        blank=True, null=True)
    
    users_need_activation = models.BooleanField(_('Users Need Activation'),
        help_text=_('If activated, newly registered users need to be approved by a portal admin before being able to log in.'),
        default=False)
    
    # css fields for custom portal styles
    background_image = models.ImageField(_('Background Image'),
        help_text=_('Used for the background of the landing and CMS-pages'),
        upload_to=get_portal_background_image_filename,
        blank=True, null=True)
    logo_image = models.ImageField(_('Logo Image'),
        help_text=_('Used as a small logo in the navigation bar and for external links to this portal'),
        upload_to=get_portal_background_image_filename,
        blank=True, null=True)
    top_color = models.CharField(_('Main color'), help_text=_('Main background color (css hex value, with or without "#")'),
        max_length=10, validators=[MaxLengthValidator(7)],
        blank=True, null=True)
    bottom_color = models.CharField(_('Gradient color'), help_text=_('Bottom color for the gradient (css hex value, with or without "#")'),
        max_length=10, validators=[MaxLengthValidator(7)],
        blank=True, null=True)
    extra_css = models.TextField(_('Extra CSS'), help_text=_('Extra CSS for this portal, will be applied after all other styles.'),
        blank=True, null=True)
    
    
    @classmethod
    def get_current(cls):
        """ Cached, returns the current Portal (always the same since dependent on configured Site) """
        portal = cache.get(CosinnusPortal._CURRENT_PORTAL_CACHE_KEY)
        if portal is None:
            portal = CosinnusPortal.objects.select_related('site').get(site=settings.SITE_ID)
            # cache indefinetly unless portal changes
            cache.set(CosinnusPortal._CURRENT_PORTAL_CACHE_KEY, portal, 60 * 60 * 24 * 365) 
        return portal
    
    def save(self, *args, **kwargs):
        # clean color fields
        self.top_color = self.top_color.replace('#', '')
        self.bottom_color = self.bottom_color.replace('#', '')
        
        super(CosinnusPortal, self).save(*args, **kwargs)
        self.compile_custom_stylesheet()
        cache.delete(self._CURRENT_PORTAL_CACHE_KEY)
    
    @property
    def admins(self):
        if self._admins is None:
            self._admins = CosinnusPortalMembership.objects.get_admins(self.pk)
        return self._admins

    def is_admin(self, user):
        """Checks whether the given user is an admin of this group"""
        uid = isinstance(user, int) and user or user.pk
        return uid in self.admins

    @property
    def members(self):
        if self._members is None:
            self._members = CosinnusPortalMembership.objects.get_members(self.pk)
        return self._members

    def is_member(self, user):
        """Checks whether the given user is a member of this group"""
        uid = isinstance(user, int) and user or user.pk
        return uid in self.members

    @property
    def pendings(self):
        if self._pendings is None:
            self._pendings = CosinnusPortalMembership.objects.get_pendings(self.pk)
        return self._pendings

    def is_pending(self, user):
        """Checks whether the given user has a pending status on this group"""
        uid = isinstance(user, int) and user or user.pk
        return uid in self.pendings
    
    def _clear_local_cache(self):
        """ Stub, called when memberships change """
        pass
    
    def get_domain(self):
        """ Gets the http/https protocol aware domain for this portal """
        return get_domain_for_portal(self)
    
    def __str__(self):
        return self.name
    
    def _get_static_folder(self):
        return os.path.join(settings.BASE_PATH, 'static') if settings.DEBUG else settings.STATIC_ROOT
    
    def compile_custom_stylesheet(self):
        """ Compiles the CSS file based on this portal's style fields and saves them 
            in the media folder """
        if settings.DEBUG:
            try:
                os.makedirs(os.path.join(settings.STATIC_ROOT, 'css'))
            except:
                pass
        custom_css = render_to_string('cosinnus/css/portal_custom_styles.css', dictionary={'portal': self})
        css_file = open(os.path.join(self._get_static_folder(), 'css', self._CUSTOM_CSS_FILENAME % self.slug), 'w')
        css_file.write(custom_css)
        css_file.close()
    
    @cached_property
    def custom_stylesheet_url(self):
        if not os.path.isfile(os.path.join(self._get_static_folder(), 'css', self._CUSTOM_CSS_FILENAME % self.slug)):
            self.compile_custom_stylesheet()
        return 'css/' + self._CUSTOM_CSS_FILENAME % self.slug
        

@python_2_unicode_compatible
class CosinnusGroup(models.Model):
    TYPE_PROJECT = 0
    TYPE_SOCIETY = 1
    
    #: Choices for :attr:`visibility`: ``(int, str)``
    TYPE_CHOICES = (
        (TYPE_PROJECT, _('Group')),
        (TYPE_SOCIETY, _('Society')),
    )
    
    GROUP_MODEL_TYPE = TYPE_PROJECT
    
    # don't worry, the default Portal with id 1 is created in a datamigration
    # there was no other way to generate completely runnable migrations 
    # (with a get_default function, or any other way)
    portal = models.ForeignKey(CosinnusPortal, verbose_name=_('Portal'), related_name='groups', 
        null=False, blank=False, default=1) # port_id 1 is created in a datamigration!
    
    name = models.CharField(_('Name'), max_length=100,
        validators=[group_name_validator])
    slug = models.SlugField(_('Slug'), 
        help_text=_('Be extremely careful when changing this slug manually! There can be many side-effects (redirects breaking e.g.)!'), 
        max_length=50)
    type = models.PositiveSmallIntegerField(_('Group Type'), blank=False,
        default=TYPE_PROJECT, choices=TYPE_CHOICES, editable=False)
    
    description = HTMLField(verbose_name=_('Short Description'),
         help_text=_('Short Description. Internal, will not be shown publicly.'), blank=True)
    description_long = HTMLField(verbose_name=_('Detailed Description'),
         help_text=_('Detailed, public description.'), blank=True)
    contact_info = HTMLField(verbose_name=_('Contact Information'),
         help_text=_('How you can be contacted - addresses, social media, etc.'), blank=True)
    
    
    avatar = models.ImageField(_("Avatar"), null=True, blank=True,
        upload_to=get_group_avatar_filename,
        max_length=250)
    wallpaper = models.ImageField(_("Wallpaper image"), 
        help_text=_('Shown as large banner image on the Microsite'),
        null=True, blank=True,
        upload_to=get_group_wallpaper_filename,
        max_length=250)
    website = models.URLField(_('Website'), max_length=100, blank=True, null=True)
    public = models.BooleanField(_('Public'), default=False)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True,
        related_name='cosinnus_groups', through='CosinnusGroupMembership')
    media_tag = models.OneToOneField(settings.COSINNUS_TAG_OBJECT_MODEL,
        blank=True, null=True, editable=False, on_delete=models.SET_NULL)
    
    # a comma-seperated list of all cosinnus apps that should not be shown in the frontend, 
    # be editable, or be indexed by search indices for this group
    deactivated_apps = models.CharField(_('Deactivated Apps'), max_length=255, 
        blank=True, null=True, editable=True)
    is_active = models.BooleanField(_('Is active'),
        help_text=_('If a group is not active, it counts as non-existent for all purposes and views on the website.'),
        default=True)
    
    parent = models.ForeignKey("self", verbose_name=_('Parent Group'),
        related_name='groups', null=True, blank=True, on_delete=models.SET_NULL)
    
    objects = CosinnusGroupManager()
    
    _portal_id = None
    
    class Meta:
        app_label = 'cosinnus'
        ordering = ('name',)
        verbose_name = _('Cosinnus group')
        verbose_name_plural = _('Cosinnus groups')
        unique_together = ('slug', 'portal', )

    def __init__(self, *args, **kwargs):
        super(CosinnusGroup, self).__init__(*args, **kwargs)
        self._admins = None
        self._members = None
        self._pendings = None
        self._portal = self.portal
        self._type = self.type
        self._slug = self.slug

    def __str__(self):
        # FIXME: better caching for .portal.name
        return '%s (%s)' % (self.name, self.portal.name)

    def save(self, *args, **kwargs):
        created = bool(self.pk is None)
        slugs = [self.slug] if self.slug else []
        self.name = clean_single_line_text(self.name)
        
        # make sure unique_aware_slugify won't come up with a slug that is already used by a 
        # PermanentRedirect pattern for an old group
        current_portal = self.portal or CosinnusPortal.get_current()
        from cosinnus.core.registries.group_models import group_model_registry
        group_type = group_model_registry.get_url_key_by_type(self.type)
        # we check if there exists a group redirect that occupies this slug (and which is not pointed to this group)
        def extra_check(slug):
            group_id_portal_id = CosinnusPermanentRedirect.get_group_id_for_pattern(current_portal, group_type, slug)
            if group_id_portal_id:
                group_id, portal_id = group_id_portal_id
                if group_id != self.id or portal_id != self.portal_id:
                    return True
            return False
        unique_aware_slugify(self, 'name', 'slug', extra_conflict_check=extra_check, force_redo=True, portal_id=current_portal)
        
        if not self.slug:
            raise ValidationError(_('Slug must not be empty.'))
        # sanity check for missing media_tag:
        if not self.media_tag:
            from cosinnus.models.tagged import get_tag_object_model
            media_tag = get_tag_object_model()._default_manager.create()
            self.media_tag = media_tag
        
        display_redirect_created_message = False
        if not created and (\
            self.portal != self._portal or \
            self.type != self._type or \
            self.slug != self._slug):
            # group is changing in a ways that would change its URI! 
            # create permanent redirect from old portal to this group
            CosinnusPermanentRedirect.create_for_pattern(self._portal, self._type, self._slug, self)
            display_redirect_created_message = True
            slugs.append(self._slug)
            
        if created and not self.portal:
            # set portal to current
            self.portal = CosinnusPortal.get_current()
        
        super(CosinnusGroup, self).save(*args, **kwargs)
        self._clear_cache(slugs=slugs, group=self)
        
        self._portal = self.portal
        self._type = self.type
        self._slug = self.slug
        
        if display_redirect_created_message:
            # possible because of AddRequestToModelSaveMiddleware
            messages.info(self.request, _('The URL for this group has changed. A redirect from all existing URLs has automatically been created!'))
        
        if created:
            # send creation signal
            signals.group_object_ceated.send(sender=self, group=self)
    
    
    def delete(self, *args, **kwargs):
        self._clear_cache(slug=self.slug)
        super(CosinnusGroup, self).delete(*args, **kwargs)

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
    def _clear_cache(self, slug=None, slugs=None, group=None):
        slugs = set([s for s in slugs]) if slugs else set()
        if slug: slugs.add(slug)
        if group: slugs.add(group.slug)
        keys = [
            self.objects._GROUPS_SLUG_CACHE_KEY % (CosinnusPortal.get_current().id, self.objects.__class__.__name__),
            self.objects._GROUPS_PK_CACHE_KEY % (CosinnusPortal.get_current().id, self.objects.__class__.__name__),
        ]
        if slug:
            keys.append(self.objects._GROUP_CACHE_KEY % (CosinnusPortal.get_current().id, self.objects.__class__.__name__, slug))
            keys.append(CosinnusGroupManager._GROUP_SLUG_TYPE_CACHE_KEY % (CosinnusPortal.get_current().id, slug))
        if slugs:
            keys.extend([self.objects._GROUP_CACHE_KEY % (CosinnusPortal.get_current().id, self.objects.__class__.__name__, s) for s in slugs])
            keys.extend([CosinnusGroupManager._GROUP_SLUG_TYPE_CACHE_KEY % (CosinnusPortal.get_current().id, s) for s in slugs])
        if group:
            group._clear_local_cache()
            if group.parent_id:
                keys.append(CosinnusGroupManager._GROUP_CHILDREN_PK_CACHE_KEY % (CosinnusPortal.get_current().id, group.parent_id))
        cache.delete_many(keys)
        
        # if this has been called on the model-ignorant CosinnusGroupManager, as a precaution, also run this for the sub-models
        if self.objects.__class__.__name__ == CosinnusGroupManager.__name__:
            for url_key in group_model_registry:
                group_class = group_model_registry.get(url_key)
                group_class._clear_cache(slug, slugs)
    
    def clear_cache(self):
        self._clear_cache(group=self)
    
    def clear_member_cache(self):
        CosinnusGroupMembership.clear_member_cache_for_group(self)

    def _clear_local_cache(self):
        self._admins = self._members = self._pendings = None
        
    @property
    def avatar_url(self):
        return self.avatar.url if self.avatar else None
    
    def _get_media_image_path(self, file_field, filename_modifier=None):
        """Gets the unique path for each image file in the media directory"""
        mediapath = os.path.join(get_cosinnus_media_file_folder(), 'avatars', 'group_wallpapers')
        mediapath_local = os.path.join(settings.MEDIA_ROOT, mediapath)
        if not os.path.exists(mediapath_local):
            os.makedirs(mediapath_local)
        filename_modifier = '_' + filename_modifier if filename_modifier else ''
        image_filename = file_field.path.split(os.sep)[-1] + filename_modifier + '.' + file_field.path.split('.')[-1]
        return os.path.join(mediapath, image_filename)
    
    def static_wallpaper_url(self, size=None, filename_modifier=None):
        """
        This function copies the image to its new path (if necessary) and
        returns the URL for the image to be displayed on the page. (Ex:
        '/media/cosinnus_files/images/dca2b30b1e07ed135c24d7dbd928e37523b474bb.jpg')

        It is a helper function to display cosinnus image files on the webpage.

        The image file is copied to a general image folder in cosinnus_files,
        so the true image path is not shown to the client.

        """
        if not self.wallpaper:
            return ''
        if not size:
            size = settings.COSINNUS_GROUP_WALLPAPER_MAXIMUM_SIZE_SCALE
            
        # the modifier can be used to save images of different sizes
        media_image_path = self._get_media_image_path(self.wallpaper, filename_modifier=filename_modifier)

        # if image is not in media dir yet, resize and copy it
        imagepath_local = os.path.join(settings.MEDIA_ROOT, media_image_path)
        if not os.path.exists(imagepath_local):
            thumbnailer = get_thumbnailer(self.wallpaper)
            try:
                thumbnail = thumbnailer.get_thumbnail({
                    'crop': 'smart',
                    'upscale': 'smart',
                    'size': size,
                })
            except InvalidImageFormatError:
                raise
            
            if not thumbnail:
                return ''
            shutil.copy(thumbnail.path, imagepath_local)
        
        media_image_path = media_image_path.replace('\\', '/')  # fix for local windows systems
        return os.path.join(settings.MEDIA_URL, media_image_path)
    
    
    def is_foreign_portal(self):
        return CosinnusPortal.get_current().id != self.portal_id
    
    def get_deactivated_apps(self):
        """ Returns a list of all cosinnus apps that have been deactivated for this group """
        if self.deactivated_apps:
            return self.deactivated_apps.split(',')
        return []
    
    def is_app_deactivated(self, app_name):
        """ Returns True if the cosinnus app with the given app_name has been deactivated for this group """
        if self.deactivated_apps:
            return app_name in self.deactivated_apps.split(',')
        return False
    
    def media_tag_object(self):
        key = '_media_tag_cache'
        if not hasattr(self, key):
            setattr(self, key, self.media_tag)
        return getattr(self, key)
    
    def get_absolute_url(self):
        return group_aware_reverse('cosinnus:group-dashboard', kwargs={'group': self})
    
    @cached_property
    def get_parent_typed(self):
        """ This is the only way to make sure to get the real object of a group's parent
            (determined by its type), and not just a generic CosinnusGroup. """ 
        if self.parent_id:
            from cosinnus.core.registries.group_models import group_model_registry
            parent = self.parent
            cls = group_model_registry.get_by_type(parent.type)
            return cls.objects.all().get(id=parent.id)
        return None
    
    def get_children(self, for_parent_id=None):
        """ Returns all CosinnusGroups that have this group as parent.
            @param for_parent_id: If supplied, will get the children for another CosinnusGroup id instead of for this group """
        for_parent_id = for_parent_id or self.id
        children_cache_key = CosinnusGroupManager._GROUP_CHILDREN_PK_CACHE_KEY % (CosinnusPortal.get_current().id, for_parent_id)
        children_ids = cache.get(children_cache_key)
        if children_ids is None:
            children_ids = CosinnusGroup.objects.filter(parent_id=for_parent_id).values_list('id', flat=True)
            cache.set(children_cache_key, children_ids, settings.COSINNUS_GROUP_CHILDREN_CACHE_TIMEOUT)
        return CosinnusProject.objects.get_cached(pks=children_ids)
    
    def get_siblings(self):
        """ If this has a parent group, returns all CosinnusGroups that also have that group
            as a parent (excluding self) """
        if not self.parent_id:
            return []
        parents_children = self.get_children(for_parent_id=self.parent_id)
        return [child for child in parents_children if not child.id == self.id]


class CosinnusProjectManager(CosinnusGroupManager):
    def get_queryset(self):
        return super(CosinnusProjectManager, self).get_queryset().filter(type=CosinnusGroup.TYPE_PROJECT)

    get_query_set = get_queryset


@python_2_unicode_compatible
class CosinnusProject(CosinnusGroup):
    
    class Meta:
        """ For some reason, the Meta isn't inherited automatically from CosinnusGroup here """
        proxy = True
        app_label = 'cosinnus'
        ordering = ('name',)
        verbose_name = _('Cosinnus project')
        verbose_name_plural = _('Cosinnus projects')
    
    GROUP_MODEL_TYPE = CosinnusGroup.TYPE_PROJECT
    
    objects = CosinnusProjectManager()
    
    def save(self, allow_type_change=False, *args, **kwargs):
        if not allow_type_change:
            self.type = CosinnusGroup.TYPE_PROJECT
        super(CosinnusProject, self).save(*args, **kwargs)
        
    def __str__(self):
        # FIXME: better caching for .portal.name
        return '%s (%s)' % (self.name, self.portal.name)

        
    
class CosinnusSocietyManager(CosinnusGroupManager):
    def get_queryset(self):
        return super(CosinnusSocietyManager, self).get_queryset().filter(type=CosinnusGroup.TYPE_SOCIETY)

    get_query_set = get_queryset


@python_2_unicode_compatible
class CosinnusSociety(CosinnusGroup):
    
    class Meta:
        """ For some reason, the Meta isn't inherited automatically from CosinnusGroup here """
        proxy = True        
        app_label = 'cosinnus'
        ordering = ('name',)
        verbose_name = _('Cosinnus society')
        verbose_name_plural = _('Cosinnus societies')
    
    GROUP_MODEL_TYPE = CosinnusGroup.TYPE_SOCIETY
    
    objects = CosinnusSocietyManager()
    
    def save(self, allow_type_change=False, *args, **kwargs):
        if not allow_type_change:
            self.type = CosinnusGroup.TYPE_SOCIETY
        super(CosinnusSociety, self).save(*args, **kwargs)
    
    def __str__(self):
        # FIXME: better caching for .portal.name
        return '%s (%s)' % (self.name, self.portal.name)

    

@python_2_unicode_compatible
class BaseGroupMembership(models.Model):
    # group = must be defined in overriding class!
    # user = must be defined in overriding class!
    status = models.PositiveSmallIntegerField(choices=MEMBERSHIP_STATUSES,
        db_index=True, default=MEMBERSHIP_PENDING)
    date = models.DateTimeField(auto_now_add=True, editable=False)

    objects = CosinnusGroupMembershipManager()
    
    CACHE_KEY_MODEL = None

    class Meta:
        abstract = True
        app_label = 'cosinnus'
        unique_together = (('user', 'group'),)  

    def __init__(self, *args, **kwargs):
        if not self.CACHE_KEY_MODEL:
            raise ImproperlyConfigured('You must define a cache key specific to ' + 
                '                        the model of this membership type!')
        super(BaseGroupMembership, self).__init__(*args, **kwargs)
        self._old_current_status = self.status

    def __str__(self):
        return "<user: %(user)s, group: %(group)s, status: %(status)d>" % {
            'user': self.user,
            'group': self.group,
            'status': self.status,
        }

    def delete(self, *args, **kwargs):
        super(BaseGroupMembership, self).delete(*args, **kwargs)
        self._clear_cache()

    def save(self, *args, **kwargs):
        # Only update the date if the the state changes from pending to member
        # or admin
        if self._old_current_status == MEMBERSHIP_PENDING and \
                self.status != self._old_current_status:
            self.date = now()
        super(BaseGroupMembership, self).save(*args, **kwargs)
        self._clear_cache()

    def _clear_cache(self):
        self.clear_member_cache_for_group(self.group)
        
    @classmethod
    def clear_member_cache_for_group(cls, group):
        cache.delete_many([
            _MEMBERSHIP_ADMINS_KEY % (cls.CACHE_KEY_MODEL, group.pk),
            _MEMBERSHIP_MEMBERS_KEY % (cls.CACHE_KEY_MODEL, group.pk), 
            _MEMBERSHIP_PENDINGS_KEY % (cls.CACHE_KEY_MODEL, group.pk),
        ])
        group._clear_local_cache()
        
    def user_email(self):
        return self.user.email
    
    
class CosinnusGroupMembership(BaseGroupMembership):
    group = models.ForeignKey(CosinnusGroup, related_name='memberships',
        on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
        related_name='cosinnus_memberships', on_delete=models.CASCADE)
    
    CACHE_KEY_MODEL = 'CosinnusGroup'
    
    class Meta(BaseGroupMembership.Meta):
        verbose_name = _('Group membership')
        verbose_name_plural = _('Group memberships')  
    

class CosinnusPortalMembership(BaseGroupMembership):
    group = models.ForeignKey(CosinnusPortal, related_name='memberships',
        on_delete=models.CASCADE, verbose_name=_('Portal'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
        related_name='cosinnus_portal_memberships', on_delete=models.CASCADE)
    
    CACHE_KEY_MODEL = 'CosinnusPortal'
    
    class Meta(BaseGroupMembership.Meta):
        verbose_name = _('Portal membership')
        verbose_name_plural = _('Portal memberships')



class CosinnusPermanentRedirect(models.Model):
    """ Sets up a redirect for all URLs that match the pattern of
        http://<from-portal-url>/<from-type>/<from-slug/ where <from-type> is one of
        cosinnus.core.registries.group_model_registry's group slug fragments. 
        If a URL requested matches this, a Middleware will redirect to <to_group> """
        
    from_portal = models.ForeignKey(CosinnusPortal, related_name='redirects',
        on_delete=models.CASCADE, verbose_name=_('From Portal'))
    from_type = models.CharField(_('From Group Type'), max_length=50)
    from_slug = models.CharField(_('From Slug'), max_length=50)
    
    to_group = models.ForeignKey(CosinnusGroup, related_name='redirects',
        on_delete=models.CASCADE, verbose_name=_('Permanent Group Redirects'))
    
    _cache_string = None
    
    CACHE_KEY = 'cosinnus/core/permanent_redirect/dict'

    
    class Meta(BaseGroupMembership.Meta):
        verbose_name = _('Permanent Group Redirect')
        verbose_name_plural = _('Permanent Group Redirects')
        unique_together = (('from_portal', 'from_type', 'from_slug'), ('from_portal', 'to_group', 'from_slug'),)
    
    def __init__(self, *args, **kwargs):
        super(CosinnusPermanentRedirect, self).__init__(*args, **kwargs)
        self._cache_string = self.cache_string
    
    @classmethod
    def make_cache_string(cls, portal_id, group_type, group_slug):
        return '%d_%s_%s' % (portal_id, group_type, group_slug)
    
    @property
    def cache_string(self):
        if not (self.from_portal_id and self.from_type and self.from_slug):
            return None
        return CosinnusPermanentRedirect.make_cache_string(self.from_portal_id, self.from_type, self.from_slug)
    
    @classmethod
    def _get_cache_dict(cls):
        cached_dict = cache.get(cls.CACHE_KEY)
        if not cached_dict:
            cached_dict = {}
            # add all Groups to cache
            current_portal = CosinnusPortal.get_current()
            for perm_redirect in CosinnusPermanentRedirect.objects. \
                        filter(from_portal=current_portal).prefetch_related('to_group'):
                to_group = perm_redirect.to_group
                cached_dict[perm_redirect.cache_string] = (to_group.id, to_group.portal_id)
            cls._set_cache_dict(cached_dict)
        return cached_dict
    
    @classmethod
    def _set_cache_dict(cls, cached_dict):
        cache.set(cls.CACHE_KEY, cached_dict, settings.COSINNUS_PERMANENT_REDIRECT_CACHE_TIMEOUT)
    
    @classmethod
    def get_group_id_for_pattern(cls, portal, group_type, group_slug):
        """ For a URL pattern, finds if there is a permanent redirect installed, and if so,
            returns the (group id, portal id) tuple of the group it should redirect to """
        try:
            redirects_dict = cls._get_cache_dict()
            cache_string = cls.make_cache_string(portal.id, group_type, group_slug)
            return redirects_dict.get(cache_string, None)
        except CosinnusGroup.DoesNotExist:
            return None
    
    @classmethod
    def get_group_for_pattern(cls, portal, group_type, group_slug):
        """ For a URL pattern, finds if there is a permanent redirect installed, and if so,
            returns the group it should redirect to """
        group_id_portal = cls.get_group_id_for_pattern(portal, group_type, group_slug) 
        if group_id_portal:
            group_id, portal_id = group_id_portal
            from cosinnus.core.registries.group_models import group_model_registry # must be lazy!
            group_cls = group_model_registry.get(group_type)
            try:
                group = group_cls.objects.get_by_id(id=group_id, portal_id=portal_id)
                return group
            except group_cls.DoesNotExist:
                pass
        return None
    
    @classmethod
    def create_for_pattern(cls, _portal, _type, _slug, to_group):
        from cosinnus.core.registries.group_models import group_model_registry # must be lazy re-import!
        group_type = group_model_registry.get_url_key_by_type(_type)
        try:
            with atomic():
                CosinnusPermanentRedirect.objects.create(from_portal=_portal, from_type=group_type, from_slug=_slug, to_group=to_group)
        except IntegrityError:
            # if any existing redirects cause integrity error, delete them, because they would cause infite redirects
            # because they conflict however, they are stale by default and can be deleted
            # delete all unique_together constraining perm redirects
            stale_redirects = CosinnusPermanentRedirect.objects.filter(
                Q(from_portal=_portal, from_type=group_type, from_slug=_slug) | \
                Q(from_portal=_portal, from_slug=_slug, to_group=to_group))
            stale_redirects.delete()
            # retry creating the redirect
            CosinnusPermanentRedirect.objects.create(from_portal=_portal, from_type=group_type, from_slug=_slug, to_group=to_group)
            # completely delete cache, checking which keys to delete would be more costly than redoing it all once
            cache.delete(CosinnusPermanentRedirect.CACHE_KEY)
        # also check if a group has a redirect pointing in on itself (and delete them)
        # (may happen when renaming a group back to its old name again)
        try:
            to_group_type = group_model_registry.get_url_key_by_type(to_group.type)
            self_redir = CosinnusPermanentRedirect.objects.get(from_portal=to_group.portal, from_slug=to_group.slug,
                                                               to_group=to_group, from_type=to_group_type)
            self_redir.delete()
        except CosinnusPermanentRedirect.DoesNotExist:
            pass
        
    def save(self, *args, **kwargs):
        created = bool(self.pk is None)
        if not created:
            # delete old group pattern from cache
            cached_dict = CosinnusPermanentRedirect._get_cache_dict()
            del cached_dict[self._cache_string]
            CosinnusPermanentRedirect._set_cache_dict(cached_dict)
        super(CosinnusPermanentRedirect, self).save(*args, **kwargs)
        
        # add group pattern to cache
        self._cache_string = self.cache_string
        cached_dict = CosinnusPermanentRedirect._get_cache_dict()
        cached_dict[self.cache_string] = (self.to_group_id, self.to_group.portal_id)
        CosinnusPermanentRedirect._set_cache_dict(cached_dict)
    
    def delete(self, *args, **kwargs):
        # delete group pattern from cache
        cached_dict = CosinnusPermanentRedirect._get_cache_dict()
        if self.cache_string in cached_dict: 
            del cached_dict[self.cache_string]
        CosinnusPermanentRedirect._set_cache_dict(cached_dict)
        super(CosinnusPermanentRedirect, self).delete(*args, **kwargs)

    
@receiver(post_delete)
def clear_cache_on_group_delete(sender, instance, **kwargs):
    """ Clears the cache on CosinnusGroups after deleting one of them. """
    if sender == CosinnusGroup or issubclass(sender, CosinnusGroup):
        instance._clear_cache(slug=instance.slug)    


def ensure_user_in_group_portal(sender, created, **kwargs):
    """ Whenever a group membership is created, make sure the user is in the Portal for this group """
    if created:
        try:
            membership = kwargs.get('instance')
            CosinnusPortalMembership.objects.get_or_create(user=membership.user, group=membership.group.portal, defaults={'status': MEMBERSHIP_MEMBER})
        except:
            # We fail silently, because we never want to 500 here unexpectedly
            logger.error("Error while trying to add User Portal Membership for user that has just joined a group.")


# makes sure that users gain membership in a Portal when they are added into a group in that portal
post_save.connect(ensure_user_in_group_portal, sender=CosinnusGroupMembership)
