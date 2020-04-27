# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import map
from builtins import object
from collections import OrderedDict
import os
import re
import six

from django.contrib.postgres.fields.jsonb import JSONField as PostgresJSONField
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

from cosinnus.conf import settings
from cosinnus.models.cms import CosinnusMicropage
from cosinnus.utils.functions import unique_aware_slugify,\
    clean_single_line_text, sort_key_strcoll_attr
from cosinnus.utils.files import get_group_avatar_filename,\
    get_portal_background_image_filename, get_group_wallpaper_filename,\
    get_cosinnus_media_file_folder, get_group_gallery_image_filename,\
    image_thumbnail, image_thumbnail_url
from django.urls import reverse
from django.utils.functional import cached_property
from cosinnus.utils.urls import group_aware_reverse, get_domain_for_portal
from cosinnus.utils.compat import atomic
from cosinnus.core import signals
from cosinnus.core.registries.group_models import group_model_registry
from django.template.loader import render_to_string

from django.db import IntegrityError
from django.contrib import messages

import logging
import shutil
from easy_thumbnails.files import get_thumbnailer
from easy_thumbnails.exceptions import InvalidImageFormatError
from django.contrib.auth import get_user_model
from cosinnus.utils.group import get_cosinnus_group_model,\
    get_default_user_group_slugs
from cosinnus.utils.user import filter_active_users
from cosinnus.models.mixins.images import ThumbnailableImageMixin
from cosinnus.views.mixins.media import VideoEmbedFieldMixin,\
    FlickrEmbedFieldMixin
from jsonfield.fields import JSONField
from django.templatetags.static import static
from cosinnus.models.mixins.indexes import IndexingUtilsMixin
from cosinnus.core.registries.attached_objects import attached_object_registry
from django.apps import apps
from cosinnus.models.tagged import LikeableObjectMixin, LastVisitedMixin
import datetime
from django.contrib.contenttypes.models import ContentType

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
    _GROUP_CHILDREN_PK_CACHE_KEY = 'cosinnus/core/portal/%d/group_children_pks/%d' # portal_id, group-pk (int) --> list ( pk (int) )
    # list of all group pks and the slug mapped to each pk
    _GROUP_LOCATIONS_CACHE_KEY = 'cosinnus/core/portal/%d/group_locations/%s/pks' # portal_id,  group-pk (int)   --> list ( CosinnusLocation )

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

    def get_pks(self, portal_id=None, force=True):
        """
        Gets all group pks from the cache or, if the can has not been filled,
        gets the pks and slugs from the database and fills the cache.
        
        @param force: if True, forces a rebuild of the pk and slug cache for this group type
        :returns: A :class:`OrderedDict` with a `pk => slug` mapping of all
            groups
        """
        if portal_id is None:
            portal_id = CosinnusPortal.get_current().id
            
        pks = cache.get(self._GROUPS_PK_CACHE_KEY % (portal_id, self.__class__.__name__))
        if force or pks is None:
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
                    
                    # attempt to cache the portal along with the group
                    if portal_id == CosinnusPortal.get_current().id:
                        group.portal = CosinnusPortal.get_current()
                    else:
                        group.portal = group.portal
                    
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
                group_list = list(groups.values())
                group_list = sorted(group_list, key=sort_key_strcoll_attr('name'))
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
                slugs = [_f for _f in (cached_pks.get(id, []) for id in pks) if _f]
                if slugs:
                    return self.get_cached(slugs=slugs, portal_id=portal_id)
                return []  # We rely on the slug and id maps being up to date
        return []
    
    def all_in_portal(self):
        """ Returns all groups within the current portal only """
        return self.get_queryset().filter(portal=CosinnusPortal.get_current(), is_active=True)

    def get(self, slug=None, portal_id=None, id=None, *args, **kwargs):
        # defer original objects.get() to manager
        if len(kwargs) > 0:
            if slug: kwargs['slug'] = slug
            if portal_id: kwargs['portal__id'] = portal_id
            if id: kwargs['id'] = id
            return super(CosinnusGroupManager, self).get(*args, **kwargs)
        # all specific queries are using the cache
        if portal_id is None:
            portal_id = CosinnusPortal.get_current().id
        if id is not None:
            return self.get_by_id(id, portal_id)
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
    
    def get_for_user_invited(self, user, includeInactive=False):
        """
        :returns: a list of :class:`CosinnusGroup` the given user is invited to.
        """
        return self.get_cached(pks=self.get_for_user_pks(user, member_status_in=[MEMBERSHIP_INVITED_PENDING], includeInactive=includeInactive))

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
    
    def get_deactivated_for_user(self, user):
        """ Returns for a user all groups and projects they are admin of that have been deactivated.
            For superusers, returns *all* deactivated groups and projects!
            Note: uncached! 
        """
        from cosinnus.utils.permissions import check_user_superuser
        all_inactive_groups = self.get_queryset().filter(portal_id=CosinnusPortal.get_current().id, is_active=False)
        
        # admins can see *all* inactive groups. for the rest of the users, filter the list to groups they are admin of.
        if check_user_superuser(user):
            my_inactive_groups = all_inactive_groups
        else:
            my_inactive_groups = all_inactive_groups.filter(id__in=self.get_for_user_group_admin_pks(user, includeInactive=True))
        return my_inactive_groups
        
    
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
            return self._get_users_for_multiple_groups(gids, _MEMBERSHIP_INVITED_PENDINGS_KEY, MEMBERSHIP_INVITED_PENDING)



@python_2_unicode_compatible
class CosinnusPortal(models.Model):
    
    _CURRENT_PORTAL_CACHE_KEY = 'cosinnus/core/portal/current'
    _ALL_PORTAL_CACHE_KEY = 'cosinnus/core/portal/all'
    
    if settings.DEBUG:
        _CUSTOM_CSS_FILENAME = '_ignoreme_cosinnus_custom_portal_%s_styles.css'
    else:
        _CUSTOM_CSS_FILENAME = 'cosinnus_custom_portal_%s_styles.css'
    
    class Meta(object):
        app_label = 'cosinnus'
        verbose_name = _('Portal')
        verbose_name_plural = _('Portals')
        
    def __init__(self, *args, **kwargs):
        super(CosinnusPortal, self).__init__(*args, **kwargs)
    
    name = models.CharField(_('Name'), max_length=100,
        validators=[group_name_validator])
    slug = models.SlugField(_('Slug'), max_length=50, unique=True, blank=True)
    
    description = models.TextField(verbose_name=_('Description'), blank=True)
    support_email = models.EmailField(verbose_name=_('Support Email'), help_text=_('This email is shown to users as contact address on many pages'), blank=True)
    website = models.URLField(_('Website'), max_length=100, blank=True, null=True)
    
    welcome_email_active = models.BooleanField(verbose_name=_('Welcome-Email sending enabled'), default=False)
    welcome_email_text = models.TextField(verbose_name=_('Welcome-Email Text'), 
        blank=True, null=True, editable=True, 
        help_text=_('If set and enabled, this text will be sent to all new users after their registration is complete.'))
    
    public = models.BooleanField(_('Public'), default=False)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True,
        related_name='cosinnus_portals', through='cosinnus.CosinnusPortalMembership')
    
    site = models.OneToOneField(Site, verbose_name=_('Associated Site'), on_delete=models.CASCADE)
    
    protocol = models.CharField(_('Http/Https Protocol (overrides settings)'), max_length=8,
                        blank=True, null=True)
    
    users_need_activation = models.BooleanField(_('Users Need Activation'),
        help_text=_('If activated, newly registered users need to be approved by a portal admin before being able to log in.'),
        default=False)
    email_needs_verification = models.BooleanField(_('Emails Need Verification'),
        help_text=_('If activated, newly registered users and users who change their email address will need to confirm their email by clicking a link in a mail sent to them.'),
        default=False)
    
    # The different keys used for this are static variables in CosinnusPortal!
    saved_infos = JSONField(default={})
    
    tos_date = models.DateTimeField(_('ToS Version'), default=datetime.datetime(1999, 1, 1, 13, 37, 0),
        help_text='This is used to determine the date the newest ToS have been released, that users have acceppted. When a portal`s ToS update, set this to a newer date to have a popup come up for all users whose `settings.tos_accepted_date` is not after this date.')
    
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
    
    video_conference_server = models.URLField(_('Video Conference Server'), max_length=250, blank=True, null=True,
        help_text=_('If entered, will enable video conference functionality across the site. Needs to be a URL up to the point where any random room name can be appended.'))
    
    # exact time when last digest was sent out for each of the period settings
    SAVED_INFO_LAST_DIGEST_SENT = 'last_digest_sent_for_period_%d'
        
    @classmethod
    def get_current(cls):
        """ Cached, returns the current Portal (always the same since dependent on configured Site) """
        portal = cache.get(CosinnusPortal._CURRENT_PORTAL_CACHE_KEY)
        if portal is None:
            portal = CosinnusPortal.objects.select_related('site').get(site=settings.SITE_ID)
            # cache indefinetly unless portal changes
            cache.set(CosinnusPortal._CURRENT_PORTAL_CACHE_KEY, portal, 60 * 60 * 24 * 365) 
        return portal
    
    @classmethod
    def get_all(cls):
        """ Cached, returns all Portals (short cache timeout to react to other sites' changes) """
        portals = cache.get(CosinnusPortal._ALL_PORTAL_CACHE_KEY)
        if portals is None:
            portals = CosinnusPortal.objects.all().select_related('site')
            cache.set(CosinnusPortal._ALL_PORTAL_CACHE_KEY, portals, 60 * 5) 
        return portals
    
    def save(self, *args, **kwargs):
        # clean color fields
        if self.top_color:
            self.top_color = self.top_color.replace('#', '')
        if self.bottom_color:
            self.bottom_color = self.bottom_color.replace('#', '')
        
        super(CosinnusPortal, self).save(*args, **kwargs)
        self.compile_custom_stylesheet()
        cache.delete(self._CURRENT_PORTAL_CACHE_KEY)
        cache.delete(self._ALL_PORTAL_CACHE_KEY)
    
    @property
    def admins(self):
        return CosinnusPortalMembership.objects.get_admins(self.pk)

    def is_admin(self, user):
        """Checks whether the given user is an admin of this group"""
        uid = isinstance(user, int) and user or user.pk
        return uid in self.admins

    @property
    def members(self):
        return CosinnusPortalMembership.objects.get_members(self.pk)

    def is_member(self, user):
        """Checks whether the given user is a member of this group"""
        uid = isinstance(user, int) and user or user.pk
        return uid in self.members

    @property
    def pendings(self):
        return CosinnusPortalMembership.objects.get_pendings(self.pk)

    def is_pending(self, user):
        """Checks whether the given user has a pending status on this group"""
        uid = isinstance(user, int) and user or user.pk
        return uid in self.pendings
    
    @property
    def invited_pendings(self):
        return CosinnusPortalMembership.objects.get_invited_pendings(self.pk)

    def is_invited_pending(self, user):
        """Checks whether the given user has a pending invitation status on this group"""
        uid = isinstance(user, int) and user or user.pk
        return uid in self.invited_pendings
    
    def _clear_local_cache(self):
        """ Stub, called when memberships change """
        pass
    
    def get_domain(self):
        """ Gets the http/https protocol aware domain for this portal """
        return get_domain_for_portal(self)
    
    def get_absolute_url(self):
        return self.get_domain()
    
    def get_logo_image_url(self):
        """ Returns the portal logo static image URL """
        return '%s%s' % (self.get_domain(), static('img/logo-icon.png'))
    
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
        custom_css = render_to_string('cosinnus/css/portal_custom_styles.css', {'portal': self})
        css_path = os.path.join(self._get_static_folder(), 'css', self._CUSTOM_CSS_FILENAME % self.slug)
        css_file = open(css_path, 'w')
        css_file.write(custom_css)
        logger.warn('Wrote Custom Portal CSS file to:', extra={'Portal': CosinnusPortal.get_current().id, 'css_path': css_path})
        css_file.close()
    
    @cached_property
    def custom_stylesheet_url(self):
        if not os.path.isfile(os.path.join(self._get_static_folder(), 'css', self._CUSTOM_CSS_FILENAME % self.slug)):
            self.compile_custom_stylesheet()
        return 'css/' + self._CUSTOM_CSS_FILENAME % self.slug
    
    @property
    def video_conference_server_url(self):
        if self.video_conference_server:
            return '%s%s-videochat' % (self.video_conference_server, CosinnusPortal.get_current().name)
        return None
    

@python_2_unicode_compatible
class CosinnusBaseGroup(LastVisitedMixin, LikeableObjectMixin, IndexingUtilsMixin, FlickrEmbedFieldMixin, 
                        VideoEmbedFieldMixin, models.Model):
    TYPE_PROJECT = 0
    TYPE_SOCIETY = 1
    
    #: Choices for :attr:`visibility`: ``(int, str)``
    TYPE_CHOICES = (
        (TYPE_PROJECT, _('Project')),
        (TYPE_SOCIETY, _('Group')),
    )
    
    GROUP_MODEL_TYPE = TYPE_PROJECT
    
    # a list of all database-fields that should be searched when looking up a group by its name
    NAME_LOOKUP_FIELDS = ['name', ]
    
    # don't worry, the default Portal with id 1 is created in a datamigration
    # there was no other way to generate completely runnable migrations 
    # (with a get_default function, or any other way)
    portal = models.ForeignKey(CosinnusPortal, verbose_name=_('Portal'), related_name='groups', 
        null=False, blank=False, default=1, on_delete=models.CASCADE) # port_id 1 is created in a datamigration!
    
    name = models.CharField(_('Name'), max_length=250) # removed validators=[group_name_validator])
    slug = models.SlugField(_('Slug'), 
        help_text=_('Be extremely careful when changing this slug manually! There can be many side-effects (redirects breaking e.g.)!'), 
        max_length=50)
    type = models.PositiveSmallIntegerField(_('Project Type'), blank=False,
        default=TYPE_PROJECT, choices=TYPE_CHOICES, editable=False)
    created = models.DateTimeField(verbose_name=_('Created'), editable=False, auto_now_add=True)
    last_modified = models.DateTimeField(verbose_name=_('Last modified'), editable=False, auto_now=True)
    
    description = models.TextField(verbose_name=_('Short Description'),
         help_text=_('Short Description. Internal, will not be shown publicly.'), blank=True)
    description_long = models.TextField(verbose_name=_('Detailed Description'),
         help_text=_('Detailed, public description.'), blank=True)
    contact_info = models.TextField(verbose_name=_('Contact Information'),
         help_text=_('How you can be contacted - addresses, social media, etc.'), blank=True)
    
    
    avatar = models.ImageField(_("Avatar"), null=True, blank=True,
        upload_to=get_group_avatar_filename,
        max_length=250)
    wallpaper = models.ImageField(_("Wallpaper image"), 
        help_text=_('Shown as large banner image on the Microsite (1140 x 240 px)'),
        null=True, blank=True,
        upload_to=get_group_wallpaper_filename,
        max_length=250)
    website = models.URLField(_('Website'), max_length=100, blank=True, null=True)
    public = models.BooleanField(_('Public'), default=False)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True,
        related_name='cosinnus_groups', through='cosinnus.CosinnusGroupMembership')
    media_tag = models.OneToOneField(settings.COSINNUS_TAG_OBJECT_MODEL,
        blank=True, null=True, editable=False, on_delete=models.SET_NULL)
    
    # microsite-embeds:
    video = models.URLField(_('Microsite Video'), max_length=200, blank=True, null=True, validators=[MaxLengthValidator(200)])
    # always contains the '@username' @ symbol!
    twitter_username = models.CharField(_('Microsite Twitter Timeline Username'), max_length=100, blank=True, null=True, validators=[MaxLengthValidator(100)])
    twitter_widget_id = models.CharField(_('Microsite Twitter Timeline Custom Widget ID'), max_length=100, blank=True, null=True)
    # Flickr gallery field, requires a flickr URL to a gallery
    flickr_url = models.URLField(_('Flickr Gallery URL'), max_length=200, blank=True, null=True, validators=[MaxLengthValidator(200)])
    
    # Call to Action Microsite Box
    call_to_action_active = models.BooleanField(_('Call to Action Microsite Box active'),
        help_text=_('If this is active, a Call to Action box will be shown on the microsite.'),
        default=False)
    call_to_action_title = models.CharField(_('Call to Action Box title'), max_length=250, validators=[MaxLengthValidator(250)],
        blank=True, null=True)
    call_to_action_description = models.TextField(verbose_name=_('Call to Action Box Description'), 
        blank=True, null=True)
    
    # a field that can contain HTML to be embedded into the group dashboard (visible for members only)
    embedded_dashboard_html = models.TextField(verbose_name=_('Embedded Dashboard HTML'),
         help_text='A field with custom HTML that will be shown to all group members on the group dashboard',
         blank=True, null=True)
    
    # a comma-seperated list of all cosinnus apps that should not be shown in the frontend, 
    # be editable, or be indexed by search indices for this group
    deactivated_apps = models.CharField(_('Deactivated Apps'), max_length=255, 
        blank=True, null=True, editable=True)
    microsite_public_apps = models.CharField(_('Microsite Public Apps'), max_length=255, 
        blank=True, null=True, editable=True)
    is_active = models.BooleanField(_('Is active'),
        help_text=_('If a team is not active, it counts as non-existent for all purposes and views on the website.'),
        default=True)
    
    facebook_group_id = models.CharField(_('Facebook Group ID'), max_length=200, 
        blank=True, null=True, validators=[MaxLengthValidator(200)])
    facebook_page_id = models.CharField(_('Facebook Page ID'), max_length=200, 
        blank=True, null=True, validators=[MaxLengthValidator(200)])
    
    nextcloud_group_id = models.CharField(_('Nextcloud Group ID'), max_length=250,
        unique=True, blank=True, null=True, validators=[MaxLengthValidator(250)])
    
    parent = models.ForeignKey("self", verbose_name=_('Parent Group'),
        related_name='groups', null=True, blank=True, on_delete=models.SET_NULL)
    related_groups = models.ManyToManyField("self", 
        through='cosinnus.RelatedGroups',
        through_fields=('to_group', 'from_group'),
        verbose_name=_('Related Teams'),
        symmetrical=False,
        blank=True, related_name='+')
    
    # this indicates that objects of this model are in some way always visible by registered users
    # on the platform, no matter their visibility settings, and thus subject to moderation 
    cosinnus_always_visible_by_users_moderator_flag = True

    settings = PostgresJSONField(default=dict, blank=True, null=True)
    
    objects = CosinnusGroupManager()
    
    _portal_id = None
    
    class Meta(object):
        abstract = True
        app_label = 'cosinnus'
        ordering = ('name',)
        verbose_name = _('Cosinnus project')
        verbose_name_plural = _('Cosinnus projects')
        unique_together = ('slug', 'portal', )

    def __init__(self, *args, **kwargs):
        super(CosinnusBaseGroup, self).__init__(*args, **kwargs)
        self._portal_id = self.portal_id
        self._type = self.type
        self._slug = self.slug

    def __str__(self):
        # FIXME: better caching for .portal.name
        return '%s (%s)' % (self.name, self.portal.name)
    
    def _get_likeable_model_name(self):
        return 'CosinnusGroup'
    
    def __getitem__(self, key):
        """ Enable accessing fields and attributed of CosinnusGroup through dict lookup. 
            This facilitates accessing group fields in the way django templates does it 
            during render time and should not have any drawbacks. 
            We use this for some multi-language swapped models of CosinnusGroup 
            in projects like DRJA where group['name'] returns group.name or 
            group.name_ru depending on the language. """
        return getattr(self, key)

    def save(self, keep_unmodified=False, *args, **kwargs):
        """ @param keep_unmodified: is de-referenced from kwargs here to support extended arguments. could be cleaner """
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
                if group_id != self.id: # or portal_id != self.portal_id: # we had this earlier, but unmatching portals with same id is not a conflict!
                    return True
            return False
        unique_aware_slugify(self, 'name', 'slug', extra_conflict_check=extra_check, force_redo=True, portal_id=current_portal)
        
        if not self.slug:
            raise ValidationError(_('Slug must not be empty.'))
        slugs.append(self.slug)
        # sanity check for missing media_tag:
        if not self.media_tag:
            from cosinnus.models.tagged import get_tag_object_model
            media_tag = get_tag_object_model()._default_manager.create()
            self.media_tag = media_tag
        
        if created and not self.portal:
            # set portal to current
            self.portal = CosinnusPortal.get_current()
        
        super(CosinnusBaseGroup, self).save(*args, **kwargs)
        
        # check if a redirect should be created AFTER SAVING!
        display_redirect_created_message = False
        if not created and (\
                self.portal_id != self._portal_id or \
                self.type != self._type or \
                self.slug != self._slug):
            # create permanent redirect from old portal to this group
            # group is changing in a ways that would change its URI! 
            old_portal = CosinnusPortal.objects.get(id=self._portal_id)
            CosinnusPermanentRedirect.create_for_pattern(old_portal, self._type, self._slug, self)
            display_redirect_created_message = True
            slugs.append(self._slug)
            
            
        self._clear_cache(slugs=slugs, group=self)
        # force rebuild the pk --> slug cache. otherwise when we query that, this group might not be in it
        self.__class__.objects.get_pks(force=True)
        
        self._portal_id = self.portal_id
        self._type = self.type
        self._slug = self.slug
        
        if display_redirect_created_message and hasattr(self, 'request'):
            # possible because of AddRequestToModelSaveMiddleware
            messages.info(self.request, _('The URL for this team has changed. A redirect from all existing URLs has automatically been created!'))
        
        if created:
            # send creation signal
            signals.group_object_ceated.send(sender=self, group=self)
    
    
    def delete(self, *args, **kwargs):
        self._clear_cache(slug=self.slug)
        super(CosinnusBaseGroup, self).delete(*args, **kwargs)

    @property
    def admins(self):
        return CosinnusGroupMembership.objects.get_admins(self.pk)
    
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
        return CosinnusGroupMembership.objects.get_members(self.pk)
    
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
        return CosinnusGroupMembership.objects.get_pendings(self.pk)

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
        return CosinnusGroupMembership.objects.get_invited_pendings(self.pk)

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
    
    def get_admin_contact_url(self):
        if settings.COSINNUS_ROCKET_ENABLED:
            return reverse('cosinnus:message-write-group', kwargs={'slug': self.slug})
        else:
            subject = _('Request about your project "%(group_name)s"') if self.type == self.TYPE_PROJECT else _('Request about your group "%(group_name)s"')
            subject = subject % {'group_name': self.name}
            return '%s?subject=%s&next=%s' % (
                reverse('postman:write', kwargs={'recipients': ':'.join([user.username for user in self.actual_admins])}),
                subject,
                reverse('postman:sent')
            )
    
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
            keys.append(CosinnusGroupManager._GROUP_CHILDREN_PK_CACHE_KEY % (CosinnusPortal.get_current().id, group.id))
            if group.parent_id:
                keys.append(CosinnusGroupManager._GROUP_CHILDREN_PK_CACHE_KEY % (CosinnusPortal.get_current().id, group.parent_id))
            keys.append(CosinnusGroupManager._GROUP_LOCATIONS_CACHE_KEY % (CosinnusPortal.get_current().id, group.id))
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
        pass
    
    def get_all_objects_for_group(self):
        """ Returns in a list all the BaseTaggableObjects for this group """
        from cosinnus.models.tagged import BaseTaggableObjectModel
        base_taggable_objects = []
        for full_model_name in attached_object_registry:
            app_label, model_name = full_model_name.split('.')
            model = apps.get_model(app_label, model_name)
            if issubclass(model, BaseTaggableObjectModel):
                instances = model.objects.filter(group=self)
                base_taggable_objects.extend(list(instances))
        return base_taggable_objects
    
    def remove_index_for_all_group_objects(self):
        """ Removes all of this group's BaseTaggableObjects from the search index """
        for instance in self.get_all_objects_for_group():
            instance.remove_index()
    
    def update_index_for_all_group_objects(self):
        """ Adds all of this group's BaseTaggableObjects to the search index """
        for instance in self.get_all_objects_for_group():
            instance.remove_index()
    
    def get_icon(self):
        """ Returns the font-awesome icon specific to the group type """
        return 'fa-group' if self.type == self.TYPE_PROJECT else 'fa-sitemap'
    
    def get_group_label(self):
        """ Returns the vocal name of the group, depending on type """
        return _('Project') if self.type == self.TYPE_PROJECT else _('Group')
    
    def get_group_menu_label(self):
        """ Returns the vocal name of the group menu, depending on type """
        return _('Project Menu') if self.type == self.TYPE_PROJECT else _('Group Menu')
    
    def get_group_dashboard_label(self):
        """ Returns the vocal name of the group dashboard, depending on type """
        return _('Project Dashboard') if self.type == self.TYPE_PROJECT else _('Group Dashboard')
    
    @property
    def avatar_url(self):
        return self.avatar.url if self.avatar else None
    
    def get_avatar_thumbnail(self, size=(80, 80)):
        return image_thumbnail(self.avatar, size)

    def get_avatar_thumbnail_url(self, size=(80, 80)):
        return image_thumbnail_url(self.avatar, size) or static('images/group-avatar-placeholder-small.png')
    
    def get_image_field_for_icon(self):
        return self.avatar or static('images/group-avatar-placeholder.png')
    
    def get_image_field_for_background(self):
        return self.wallpaper
    
    def get_facebook_avatar_url(self):
        page_or_group_id = self.facebook_page_id or self.facebook_group_id or None
        if page_or_group_id:
            return 'https://graph.facebook.com/%s/picture?type=square' % page_or_group_id
        return ''
    
    def get_locations(self):
        """ Returns a list of this group locations, similar to calling ``group.locations.all()``, but 
            attempts to fetch the locations from cache """
        locations = cache.get(CosinnusGroupManager._GROUP_LOCATIONS_CACHE_KEY % (CosinnusPortal.get_current().id, self.id))
        if locations is None:
            locations = list(self.locations.all())
            cache.set(CosinnusGroupManager._GROUP_LOCATIONS_CACHE_KEY % (CosinnusPortal.get_current().id, self.id),
                  locations, settings.COSINNUS_GROUP_LOCATIONS_CACHE_TIMEOUT)
        return locations
    
    @property
    def is_default_user_group(self):
        return self.slug in get_default_user_group_slugs()
    
    @property
    def is_forum_group(self):
        return self.slug == getattr(settings, 'NEWW_FORUM_GROUP_SLUG', None)
        
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
            except (InvalidImageFormatError, OSError, Exception):
                if settings.DEBUG:
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
    
    def get_microsite_public_apps(self):
        """ Returns a list of cosinnus apps whose public objects should be shown on the microsite.
            If not set, used the default setting in COSINNUS_MICROSITE_DEFAULT_PUBLIC_APPS """
        if getattr(self, 'microsite_public_apps', None):
            return self.microsite_public_apps.split(',')
        else:
            return settings.COSINNUS_MICROSITE_DEFAULT_PUBLIC_APPS
    
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
    
    def get_member_page_url(self):
        return group_aware_reverse('cosinnus:group-detail', kwargs={'group': self})
    
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
        from cosinnus.models.group_extra import CosinnusProject
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
    
    def get_content_type_for_last_visited(self):
        """ Overriding from `LastVisitedMixin` to always use the same group ct """
        return ContentType.objects.get_for_model(get_cosinnus_group_model())
    

class CosinnusGroup(CosinnusBaseGroup):

    class Meta(CosinnusBaseGroup.Meta):
        swappable = 'COSINNUS_GROUP_OBJECT_MODEL'


class RelatedGroups(models.Model):
    """ Need to have this through model for CosinnusGroup.related_groups so django doesn't mix up model names
        in apps that have swapped out the CosinnusGroup model """
        
    class Meta(object):
        unique_together = (('from_group', 'to_group'),)  
        
    from_group = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL, on_delete=models.CASCADE, related_name='+')
    to_group = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL, on_delete=models.CASCADE, related_name='+')


@python_2_unicode_compatible
class BaseGroupMembership(models.Model):
    # group = must be defined in overriding class!
    # user = must be defined in overriding class!
    status = models.PositiveSmallIntegerField(choices=MEMBERSHIP_STATUSES,
        db_index=True, default=MEMBERSHIP_PENDING)
    date = models.DateTimeField(auto_now_add=True, editable=False)
    # moderator status for portals, unused for groups as of now
    is_moderator = models.BooleanField(_('Is Moderator'), default=False)

    objects = CosinnusGroupMembershipManager()
    
    CACHE_KEY_MODEL = None

    class Meta(object):
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
            'user': getattr(self, 'user', None),
            'group': getattr(self, 'group', None),
            'status': self.status,
        }

    def delete(self, *args, **kwargs):
        super(BaseGroupMembership, self).delete(*args, **kwargs)
        # run an empty save on user so userprofile search indices get updated with new memberships through signals
        self.user.cosinnus_profile.save()
        self._clear_cache()

    def save(self, *args, **kwargs):
        # Only update the date if the the state changes from pending to member
        # or admin
        if (self._old_current_status == MEMBERSHIP_PENDING or self._old_current_status == MEMBERSHIP_INVITED_PENDING) and \
                (self.status == MEMBERSHIP_ADMIN or self.status == MEMBERSHIP_MEMBER):
            self.date = now()
        super(BaseGroupMembership, self).save(*args, **kwargs)
        # run an empty save on user so userprofile search indices get updated with new memberships through signals
        if hasattr(self, 'user'):
            self.user.cosinnus_profile.save()
        self._clear_cache()

    def _clear_cache(self):
        self.clear_member_cache_for_group(self.group)
        
    @classmethod
    def clear_member_cache_for_group(cls, group):
        cache.delete_many([
            _MEMBERSHIP_ADMINS_KEY % (cls.CACHE_KEY_MODEL, group.pk),
            _MEMBERSHIP_MEMBERS_KEY % (cls.CACHE_KEY_MODEL, group.pk), 
            _MEMBERSHIP_PENDINGS_KEY % (cls.CACHE_KEY_MODEL, group.pk),
            _MEMBERSHIP_INVITED_PENDINGS_KEY % (cls.CACHE_KEY_MODEL, group.pk),
        ])
        group._clear_local_cache()
        
    def user_email(self):
        return self.user.email
    
    
class CosinnusGroupMembership(BaseGroupMembership):
    group = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL, related_name='memberships',
        on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
        related_name='cosinnus_memberships', on_delete=models.CASCADE)
    
    CACHE_KEY_MODEL = 'CosinnusGroup'
    
    class Meta(BaseGroupMembership.Meta):
        verbose_name = _('Team membership')
        verbose_name_plural = _('Team memberships')  
        
    def __init__(self, *args, **kwargs):
        super(CosinnusGroupMembership, self).__init__(*args, **kwargs)
        self._status = self.status
        
    def save(self, *args, **kwargs):
        """ Checks and fires `user_joined_group` signal if a user has hereby joined this group """
        created = bool(self.pk is None)
        super(CosinnusGroupMembership, self).save(*args, **kwargs)
        created_as_membership = bool(created and self.status in MEMBER_STATUS)
        changed_to_membership = bool(not created and self._status not in MEMBER_STATUS and self.status in MEMBER_STATUS)
        if created_as_membership or changed_to_membership:
            signals.user_joined_group.send(sender=self, user=self.user, group=self.group)
    
    def delete(self, *args, **kwargs):
        """ Checks and fires `user_left_group` signal if a user has hereby left this group """
        super(CosinnusGroupMembership, self).delete(*args, **kwargs)
        signals.user_left_group.send(sender=self.group, user=self.user, group=self.group)
    

class CosinnusPortalMembership(BaseGroupMembership):
    group = models.ForeignKey(CosinnusPortal, related_name='memberships',
        on_delete=models.CASCADE, verbose_name=_('Portal'))
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
        related_name='cosinnus_portal_memberships', on_delete=models.CASCADE)
    
    CACHE_KEY_MODEL = 'CosinnusPortal'
    
    class Meta(BaseGroupMembership.Meta):
        verbose_name = _('Portal membership')
        verbose_name_plural = _('Portal memberships')
        
        
class CosinnusUnregisterdUserGroupInvite(BaseGroupMembership):
    """ A placeholder for a  group invite of person's who has been invited via email to join.
        Used to imprint a real `CosinnusGroupMembership` once that user registers.
        The ``status`` field is ignored because it would always be on pending anyways. """
        
    group = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL, related_name='unregistered_user_invites',
        on_delete=models.CASCADE)
    email = models.EmailField(_('email address'))
    invited_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
        related_name='cosinnus_unregistered_user_invitations', on_delete=models.SET_NULL)
    last_modified = models.DateTimeField(_('Last modified'), auto_now=True, editable=False)
    
    CACHE_KEY_MODEL = 'CosinnusUnregisterdUserGroupInvite'
    
    class Meta(object):
        app_label = 'cosinnus'
        verbose_name = _('Team Invite for Unregistered User')
        verbose_name_plural = _('Team Invites for Unregistered Users')  
        unique_together = (('email', 'group'),)  


@python_2_unicode_compatible
class CosinnusGroupInviteToken(models.Model):
    # determines on which portal the token will be accessible for users
    portal = models.ForeignKey(CosinnusPortal, verbose_name=_('Portal'), related_name='group_invite_tokens', 
        null=False, blank=False, default=1, on_delete=models.CASCADE) # port_id 1 is created in a datamigration!
    
    title = models.CharField(_('Title'), max_length=250)
    token = models.SlugField(_('Token'), 
        help_text=_('The token string. It will be displayed as it is, but when users enter it, upper/lower-case do not matter. Can contain letters and numbers, but no spaces, and can be as long or short as you want.'), 
        max_length=50,
        null=False, blank=False)
    created = models.DateTimeField(verbose_name=_('Created'), editable=False, auto_now_add=True)
    description = models.TextField(verbose_name=_('Short Description'),
         help_text=_('Short Description (optional). Will be shown on the token page.'), blank=True)
    
    is_active = models.BooleanField(_('Is active'),
        help_text='If a token is not active, users will see an error message when trying to use it.',
        default=True)
    # valid_until is unused for now
    valid_until = models.DateTimeField(verbose_name=_('Valid until'), editable=False, blank=True, null=True)
    
    invite_groups = models.ManyToManyField(settings.COSINNUS_GROUP_OBJECT_MODEL, 
        verbose_name=_('Invite-Groups'),
        blank=False, related_name='+')
    
    
    class Meta(object):
        ordering = ('created',)
        verbose_name = _('Cosinnus Group Invite Token')
        verbose_name_plural = _('Cosinnus Group Invite Tokens')
        unique_together = ('token', 'portal', )

    def __init__(self, *args, **kwargs):
        super(CosinnusGroupInviteToken, self).__init__(*args, **kwargs)
        self._portal_id = self.portal_id
        self._token = self.token
        
    def __str__(self):
        return '<Cosinnus Token "%s" (Portal %d)' % (self.token, self.portal_id)
    
    def save(self, *args, **kwargs):
        created = bool(self.pk is None)
        self.title = clean_single_line_text(self.title)
        self.token = clean_single_line_text(self.token)
        
        # token case-insensitive unique validation
        if not self.token:
            raise ValidationError(_('Token must not be empty.'))
        current_portal = self.portal or CosinnusPortal.get_current()
        other_tokens = self.__class__.objects.filter(portal=current_portal, token__iexact=self.token)
        if not created:
            other_tokens = other_tokens.exclude(pk=self.pk)
        if other_tokens.count() > 0:
            raise ValidationError(_('A token with the same code already exists! Please choose a different string for your token.'))
        
        # set portal to current
        if created and not self.portal:
            self.portal = CosinnusPortal.get_current()
        
        super(CosinnusGroupInviteToken, self).save(*args, **kwargs)
        
        self._portal_id = self.portal_id
        self._token = self.token
        

class CosinnusPermanentRedirect(models.Model):
    """ Sets up a redirect for all URLs that match the pattern of
        http://<from-portal-url>/<from-type>/<from-slug/ where <from-type> is one of
        cosinnus.core.registries.group_model_registry's group slug fragments. 
        If a URL requested matches this, a Middleware will redirect to <to_group> """
        
    from_portal = models.ForeignKey(CosinnusPortal, related_name='redirects',
        on_delete=models.CASCADE, verbose_name=_('From Portal'))
    from_type = models.CharField(_('From Team Type'), max_length=50)
    from_slug = models.CharField(_('From Slug'), max_length=50)
    
    to_group = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL, related_name='redirects',
        on_delete=models.CASCADE, verbose_name=_('Permanent Team Redirects'))
    
    _cache_string = None
    
    CACHE_KEY = 'cosinnus/core/permanent_redirect/dict'

    
    class Meta(BaseGroupMembership.Meta):
        verbose_name = _('Permanent Team Redirect')
        verbose_name_plural = _('Permanent Team Redirects')
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
            try:
                group = CosinnusGroup.objects.get_by_id(id=group_id, portal_id=portal_id)
                return group
            except CosinnusGroup.DoesNotExist:
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
        
        # Bugfixing a heisenbug: after saving, check if this redirect violates integrity.
        # if so, immediately delete it, and report error:
        if not self.check_integrity():
            import traceback
            logger.error('Prevented a bad redirect-loop from saving itself! Deleted the loop, but TODO: find the cause! Traceback in extra. ', extra={'trace': traceback.format_exc()})
            self.delete()
            return
            
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
    
    def check_integrity(self):
        """ Checks if this redirect is valid (doesn't point at itself for an infinite loop) 
            @return: True if the redirect looks stable, False if it would cause a loop """
        to_type = group_model_registry.get_url_key_by_type(self.to_group._type)
        
        if to_type == self.from_type and self.to_group.slug == self.from_slug and \
                 self.to_group.portal_id == self.from_portal_id:
            return False
        return True
    

from osm_field.fields import OSMField, LatitudeField, LongitudeField

class CosinnusLocation(models.Model):
    
    location = OSMField(_('Location'), blank=True, null=True)
    location_lat = LatitudeField(_('Latitude'), blank=True, null=True)
    location_lon = LongitudeField(_('Longitude'), blank=True, null=True)

    group = models.ForeignKey(
        settings.COSINNUS_GROUP_OBJECT_MODEL,
        verbose_name=_('Team'),
        on_delete=models.CASCADE,
        related_name='locations',
    )
    
    class Meta(object):
        verbose_name = _('CosinnusLocation')
        verbose_name_plural = _('CosinnusLocations')
        
    @property
    def location_url(self):
        if not self.location_lat or not self.location_lon:
            return None
        return 'http://www.openstreetmap.org/?mlat=%s&mlon=%s&zoom=15&layers=M' % (self.location_lat, self.location_lon)
    
    def save(self, *args, **kwargs):
        super(CosinnusLocation, self).save(*args, **kwargs)
        if getattr(self, 'group_id'):
            cache.delete(CosinnusGroupManager._GROUP_LOCATIONS_CACHE_KEY % (CosinnusPortal.get_current().id, self.group_id))
    

class CosinnusGroupGalleryImage(ThumbnailableImageMixin, models.Model):
    
    title = models.CharField(_('Title'), max_length=250, null=True, blank=True) 
    description = models.TextField(verbose_name=_('Description'),
         null=True, blank=True)
    
    image = models.ImageField(_("Group Image"),
        upload_to=get_group_gallery_image_filename,
        max_length=250)

    group = models.ForeignKey(
        settings.COSINNUS_GROUP_OBJECT_MODEL,
        verbose_name=_('Team'),
        on_delete=models.CASCADE,
        related_name='gallery_images',
    )
    
    image_attr_name = 'image'
    
    class Meta(object):
        verbose_name = _('CosinnusGroup GalleryImage')
        verbose_name_plural = _('CosinnusGroup GalleryImages')
        
    @property
    def image_url(self):
        return self.image.url if self.image else None
    
    
class CosinnusGroupCallToActionButton(models.Model):
    
    label = models.CharField(_('Title'), max_length=250, null=False, blank=False) 
    url = models.URLField(_('URL'), max_length=200, blank=False, null=False, validators=[MaxLengthValidator(200)])
    
    group = models.ForeignKey(
        settings.COSINNUS_GROUP_OBJECT_MODEL,
        verbose_name=_('Team'),
        on_delete=models.CASCADE,
        related_name='call_to_action_buttons',
    )
    
    class Meta(object):
        verbose_name = _('CosinnusGroup CallToAction Button')
        verbose_name_plural = _('CosinnusGroup CallToAction Buttons')


def replace_swapped_group_model():
    """ Permanently replace cosinnus.models.CosinnusGroup with the final Swapped-in Model
        
        We replace the final swapped object into the class objects here, so
        late imports of CosinnusGroup always get the correct model, even if they are ignorant of get_cosinnus_group_model()
    """
    global CosinnusGroup
    CosinnusGroup = get_cosinnus_group_model()
