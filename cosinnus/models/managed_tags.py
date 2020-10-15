# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from collections import OrderedDict
import logging

from annoying.functions import get_object_or_None
from django.apps import apps
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
import six

from cosinnus.conf import settings
from cosinnus.utils.files import get_managed_tag_image_filename, image_thumbnail, \
    image_thumbnail_url
from cosinnus.utils.functions import clean_single_line_text, resolve_class


logger = logging.getLogger('cosinnus')

_CosinnusPortal = None
def CosinnusPortal():
    global _CosinnusPortal
    if _CosinnusPortal is None: 
        _CosinnusPortal = apps.get_model('cosinnus', 'CosinnusPortal')
    return _CosinnusPortal


class CosinnusManagedTagLabels(object):
    
    ICON = 'fa-tags'
    
    MANAGED_TAG_NAME = _('Managed Tag')
    MANAGED_TAG_NAME_PLURAL = _('Managed Tag')
    
    CREATE_MANAGED_TAG = _('Create Managed Tag')
    EDIT_MANAGED_TAG = _('Edit Managed Tag')
    DELETE_MANAGED_TAG = _('Delete Managed Tag')
    
    ASSIGNMENT_VERBOSE_NAME = _('Managed Tag Assignment')
    ASSIGNMENT_VERBOSE_NAME_PLURAL = _('Managed Tag Assignments')
    
    # formfield title
    MANAGED_TAG_FIELD_LABEL = MANAGED_TAG_NAME
    # formfield description for content objects (groups, content, etc)
    MANAGED_TAG_FIELD_LEGEND_CONTENT = None
    # formfield description for the user profile
    MANAGED_TAG_FIELD_LEGEND_PROFILE = None
    # in the select list, this is the "none chosen" choice string
    MANAGED_TAG_FIELD_EMPTY_CHOICE = _('No Tag selected')
    

# allow dropin of labels class
MANAGED_TAG_LABELS = CosinnusManagedTagLabels
if getattr(settings, 'COSINNUS_MANAGED_TAGS_LABEL_CLASS_DROPIN', None):
    MANAGED_TAG_LABELS = resolve_class(settings.COSINNUS_MANAGED_TAGS_LABEL_CLASS_DROPIN)


class CosinnusManagedTagManager(models.Manager):
    
    def all_in_portal(self):
        """ Returns all groups within the current portal only """
        # TODO: cache!
        return self.get_queryset().filter(portal=CosinnusPortal().get_current())
    
    def get_cached(self, pk_or_id_or_list):
        """ Returns one or many cached tags, by any given combination of a single int pk,
            str slug or a list of both combinations.
            @param pk_or_id_or_list: int or str or list of int or strs to return tag by pk or slug """
        
        if not pk_or_id_or_list:
            return [] if pk_or_id_or_list == [] else None
        single = isinstance(pk_or_id_or_list, six.string_types) or isinstance(pk_or_id_or_list, int)
        if single:
            pk_or_id_or_list = [pk_or_id_or_list]
        
        # TODO cache the dicts!
        all_tags = self.all_in_portal()
        tag_dict = dict([(tag.id, tag) for tag in all_tags] + [(tag.slug, tag) for tag in all_tags])
        
        tags = []
        for pk_or_slug in pk_or_id_or_list:
            tags.append(tag_dict.get(pk_or_slug, None))
        if single:
            return tags[0]
        return tags
        
    
#     # main pk to object key
#     _MANAGED_TAGS_PK_CACHE_KEY = 'cosinnus/core/portal/%d/managedtags/pks/%d' # portal_id, slug -> idea
#     # (pk -> slug) dict
#     _MANAGED_TAGS_SLUG_TO_PK_CACHE_KEY = 'cosinnus/core/portal/%d/managedtags/slugs' # portal_id -> {(slug, pk), ...} 
#     
#     def get_cached(self, slugs=None, pks=None, select_related_media_tag=True, portal_id=None):
#         """
#         Gets all ideas defined by either `slugs` or `pks`.
# 
#         `slugs` and `pks` may be a list or tuple of identifiers to use for
#         request where the elements are of type string / unicode or int,
#         respectively. You may provide a single string / unicode or int directly
#         to query only one object.
# 
#         :returns: An instance or a list of instances of :class:`CosinnusGroup`.
#         :raises: If a single object is defined a `CosinnusGroup.DoesNotExist`
#             will be raised in case the requested object does not exist.
#         """
#         if portal_id is None:
#             portal_id = CosinnusPortal().get_current().id
#             
#         # Check that at most one of slugs and pks is set
#         assert not (slugs and pks)
#         assert not (slugs or pks)
#             
#         if slugs is not None:
#             if isinstance(slugs, six.string_types):
#                 # We request a single idea
#                 slugs = [slugs]
#                 
#             # We request multiple ideas by slugs
#             keys = [self._IDEAS_SLUG_CACHE_KEY % (portal_id, s) for s in slugs]
#             ideas = cache.get_many(keys)
#             missing = [key.split('/')[-1] for key in keys if key not in ideas]
#             if missing:
#                 # we can only find ideas via this function that are in the same portal we run in
#                 query = self.get_queryset().filter(portal__id=portal_id, is_active=True, slug__in=missing)
#                 if select_related_media_tag:
#                     query = query.select_related('media_tag')
#                 
#                 for idea in query:
#                     ideas[self._IDEAS_SLUG_CACHE_KEY % (portal_id, idea.slug)] = idea
#                 cache.set_many(ideas, settings.COSINNUS_IDEA_CACHE_TIMEOUT)
#             
#             # sort by a good sorting function that acknowldges umlauts, etc, case insensitive
#             idea_list = list(ideas.values())
#             idea_list = sorted(idea_list, key=sort_key_strcoll_attr('name'))
#             return idea_list
#             
#         elif pks is not None:
#             if isinstance(pks, int):
#                 pks = [pks]
#             else:
#                 # We request multiple ideas
#                 cached_pks = self.get_pks(portal_id=portal_id)
#                 slugs = [_f for _f in (cached_pks.get(pk, []) for pk in pks) if _f]
#                 if slugs:
#                     return self.get_cached(slugs=slugs, portal_id=portal_id)
#                 return []  # We rely on the slug and id maps being up to date
#         return []
#     
#     
#     def get_pks(self, portal_id=None, force=True):
#         """
#         Gets the (pks -> slug) :class:`OrderedDict` from the cache or, if the can has not been filled,
#         gets the pks and slugs from the database and fills the cache.
#         
#         @param force: if True, forces a rebuild of the pk and slug cache for this group type
#         :returns: A :class:`OrderedDict` with a `pk => slug` mapping of all
#             groups
#         """
#         if portal_id is None:
#             portal_id = CosinnusPortal().get_current().id
#             
#         pks = cache.get(self._IDEAS_PK_TO_SLUG_CACHE_KEY % (portal_id))
#         if force or pks is None:
#             # we can only find groups via this function that are in the same portal we run in
#             pks = OrderedDict(self.filter(portal__id=portal_id, is_active=True).values_list('id', 'slug').all())
#             cache.set(self._IDEAS_PK_TO_SLUG_CACHE_KEY % (portal_id), pks,
#                 settings.COSINNUS_IDEA_CACHE_TIMEOUT)
#         return pks

    
    

class CosinnusManagedTagAssignmentQS(models.query.QuerySet):
    
    def tag_ids(self):
        """ Returns all CosinnusManagedTag IDs from the set of assignements """
        return self.distinct().values_list('managed_tag__id', flat=True)
    
    def tag_slugs(self):
        """ Returns all CosinnusManagedTag slugs from the set of assignements """
        return self.distinct().values_list('managed_tag__slug', flat=True)
    
    def approved(self):
        return self.filter(approved=True)
    

class CosinnusManagedTagAssignmentManager(models.Manager):
    
    def get_queryset(self):
        return CosinnusManagedTagAssignmentQS(self.model, using=self._db).select_related('managed_tag')
    
    def all_approved(self):
        return self.get_queryset().filter(approved=True)
    
    
class CosinnusManagedTagAssignment(models.Model):
    """ The assignment intermediate-Model for CosinnusManagedTag """
    
    managed_tag = models.ForeignKey('cosinnus.CosinnusManagedTag', related_name='assignments', on_delete=models.CASCADE)
    
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target_object = GenericForeignKey('content_type', 'object_id')
    
    assigners = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='managed_tag_assignments', blank=True,
        help_text='A list of people who suggested making this assignment. Can be empty, and can beignored once `approved` is True.')
    approved = models.BooleanField(verbose_name=_('Approved'), default=False)
    last_modified = models.DateTimeField(verbose_name=_('Last modified'), editable=False, auto_now=True)

    objects = CosinnusManagedTagManager()

    class Meta(object):
        app_label = 'cosinnus'
        unique_together = (('managed_tag', 'content_type', 'object_id'),)
        verbose_name = MANAGED_TAG_LABELS.ASSIGNMENT_VERBOSE_NAME
        verbose_name_plural = MANAGED_TAG_LABELS.ASSIGNMENT_VERBOSE_NAME_PLURAL

    def __str__(self):
        return "<managed tag assignment: %(managed_tag)s, content_type: %(content_type)s, target_object_id: %(target_object_id)d>" % {
            'managed_tag': getattr(self, 'managed_tag', None),
            'content_type': getattr(self, 'content_type', None),
            'target_object_id': getattr(self, 'object_id', None),
        }
        
    @classmethod
    def update_assignments_for_object(cls, obj, tag_slugs_to_assign=None):
        """ Will assign all given CosinnusManagedTags to the given object and remove existing assignments 
            not contained in the given assignment list.
            @param obj: Any object to assign the managed tags to
            @param tag_slugs_to_assign: A list of slugs of CosinnusManagedTags. Only those slugs that actually
                exist will be assigned. If None or an empty list is given, all assignments will be removed from
                the object. """
        if not obj.pk:
            logger.error('Could not save CosinnusManagedTags assignments: target object has not been saved yet!', extra={obj})
            return
        content_type = ContentType.objects.get_for_model(obj._meta.model)
        assigned_slugs = list(cls.objects.filter(
                content_type=content_type, object_id=obj.id
            ).values_list('managed_tag__slug', flat=True))
        slugs_to_assign = [slug for slug in tag_slugs_to_assign if not slug in assigned_slugs]
        slugs_to_remove = [slug for slug in assigned_slugs if not slug in tag_slugs_to_assign]
        
        # remove unwanted existing tags
        cls.objects.filter(
                content_type=content_type, object_id=obj.id, managed_tag__slug__in=slugs_to_remove
            ).delete()
        # add wanted non-existant tags
        for slug in slugs_to_assign:
            # todo: cache!
            managed_tag = get_object_or_None(CosinnusManagedTag, portal=CosinnusPortal().get_current(), slug=slug)
            if managed_tag:
                approve = not bool(settings.COSINNUS_MANAGED_TAGS_USER_TAGS_REQUIRE_APPROVAL)
                cls.objects.create(content_type=content_type, object_id=obj.id, managed_tag=managed_tag, approved=approve)


@python_2_unicode_compatible
class CosinnusManagedTag(models.Model):
    
    # don't worry, the default Portal with id 1 is created in a datamigration
    # there was no other way to generate completely runnable migrations 
    # (with a get_default function, or any other way)
    portal = models.ForeignKey('cosinnus.CosinnusPortal', verbose_name=_('Portal'), related_name='managed_tags', 
        null=False, blank=False, default=1, on_delete=models.CASCADE) # port_id 1 is created in a datamigration!
    
    name = models.CharField(_('Name'), max_length=250) 
    slug = models.SlugField(_('Slug'), 
        help_text=_('Be extremely careful when changing this slug manually! There can be many side-effects (redirects breaking e.g.)!'), 
        max_length=50)
    
    description = models.TextField(verbose_name=_('Short Description'), blank=True)
    
    image = models.ImageField(_("Image"), 
        null=True, blank=True,
        upload_to=get_managed_tag_image_filename,
        max_length=250)
    url = models.URLField(_('URL'), max_length=200, blank=True, null=True, validators=[MaxLengthValidator(200)])
    color = models.CharField(_('Color'),
         max_length=10, validators=[MaxLengthValidator(7)],
         help_text=_('Optional color code (css hex value, with or without "#")'),
         blank=True, null=True)
    
    paired_group = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL, 
        verbose_name=_('Paired Group'),
        blank=True, null=True, related_name='paired_managed_tag',
        on_delete=models.SET_NULL,
        help_text=_('A paired group will automatically be joined by all users assigned to this object.'))
    search_synonyms = models.TextField(_('Search Synonyms'),
        blank=True, null=True,
        help_text=_('Comma-seperated list of phrases for which auto-complete matches, even partial, will return this object.'))
    
    created = models.DateTimeField(verbose_name=_('Created'), editable=False, auto_now_add=True)
    creator = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_('Creator'), on_delete=models.CASCADE,
        null=True, blank=True, related_name='+')
    last_modified = models.DateTimeField( verbose_name=_('Last modified'), editable=False, auto_now=True)
    
    
    objects = CosinnusManagedTagManager()
    
    # the label object, swappable per portal
    labels = MANAGED_TAG_LABELS
    
    class Meta(object):
        ordering = ('name',)
        verbose_name = MANAGED_TAG_LABELS.MANAGED_TAG_NAME
        verbose_name_plural = MANAGED_TAG_LABELS.MANAGED_TAG_NAME_PLURAL
        unique_together = (('slug', 'portal'), )

    def __str__(self):
        return '%s (Portal %d)' % (self.name, self.portal_id)
    
    def get_icon(self):
        """ Returns the font-awesome icon specific to this object type """
        return MANAGED_TAG_LABELS.ICON
    
    def save(self, *args, **kwargs):
        created = bool(self.pk is None)
        slugs = [self.slug] if self.slug else []
        self.name = clean_single_line_text(self.name)
        
        current_portal = self.portal or CosinnusPortal().get_current()
        
        if not self.slug:
            raise ValidationError(_('Slug must not be empty.'))
        slugs.append(self.slug)
        
        # set portal to current
        if created and not self.portal:
            self.portal = current_portal
            
        super(CosinnusManagedTag, self).save(*args, **kwargs)
        
        # todo: caching
        # self._clear_cache(slugs=slugs)
        # force rebuild the pk --> slug cache. otherwise when we query that, this group might not be in it
        # self.__class__.objects.get_pks(force=True)
        
        self._portal_id = self.portal_id
        self._slug = self.slug
    
    def delete(self, *args, **kwargs):
        # todo: caching
        #self._clear_cache(slug=self.slug)
        super(CosinnusManagedTag, self).delete(*args, **kwargs)
        
    @classmethod
    def _clear_cache(self, slug=None, slugs=None):
        # todo: caching
        slugs = set([s for s in slugs]) if slugs else set()
        if slug: slugs.add(slug)
        keys = [
            self.objects._IDEAS_PK_TO_SLUG_CACHE_KEY % (CosinnusPortal().get_current().id),
        ]
        if slugs:
            keys.extend([self.objects._IDEAS_SLUG_CACHE_KEY % (CosinnusPortal().get_current().id, s) for s in slugs])
        cache.delete_many(keys)
        
    def clear_cache(self):
        # todo: caching
        self._clear_cache(slug=self.slug)
        
    @property
    def image_url(self):
        return self.image.url if self.image else None
    
    def get_image_thumbnail(self, size=(0, 80)):
        return image_thumbnail(self.image, size)

    def get_image_thumbnail_url(self, size=(0, 80)):
        return image_thumbnail_url(self.image, size)
    
    def get_absolute_url(self):
        """ Returns the assigned url field's url """
        return self.url or ''
    
    def get_search_url(self):
        """ Returns the filtered search view for this tag """
        # todo
        return '???'
    

class CosinnusManagedTagAssignmentModelMixin(object):
    """ Mixin for models that can have CosinnusManagedTagAssignments assigned. 
        You still need to add 
        `managed_tag_assignments = GenericRelation('cosinnus.CosinnusManagedTagAssignment')` 
        to your model. """
    
    def get_managed_tags(self):
        """ Returns all managed tags approved for this profile """
        tag_ids = self.managed_tag_assignments.all().filter(approved=True).values_list('managed_tag', flat=True)
        return CosinnusManagedTag.objects.get_cached(list(tag_ids))

