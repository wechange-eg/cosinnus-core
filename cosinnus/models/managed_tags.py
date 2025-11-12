# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from builtins import object

import six
from annoying.functions import get_object_or_None
from django.apps import apps
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator
from django.db import models
from django.urls.base import reverse
from django.utils.encoding import force_str
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from cosinnus.conf import settings
from cosinnus.core import signals
from cosinnus.utils.files import get_managed_tag_image_filename, image_thumbnail, image_thumbnail_url
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
    MANAGED_TAG_NAME_PLURAL = _('Managed Tags')
    MANAGED_TAG_MAP_LABEL = MANAGED_TAG_NAME_PLURAL

    MANAGED_TAG_TYPE_NAME = _('Managed Tag Type')
    MANAGED_TAG_TYPE_NAME_PLURAL = _('Managed Tag Types')

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

    @classmethod
    def get_labels_dict(cls):
        """Returns a dict of all labels.
        Note: lazy translation objects will be resolved here!"""
        return dict([(key, force_str(val)) for (key, val) in cls.__dict__.items() if not key.startswith('_')])


# allow dropin of labels class
MANAGED_TAG_LABELS = CosinnusManagedTagLabels
if getattr(settings, 'COSINNUS_MANAGED_TAGS_LABEL_CLASS_DROPIN', None):
    MANAGED_TAG_LABELS = resolve_class(settings.COSINNUS_MANAGED_TAGS_LABEL_CLASS_DROPIN)


class CosinnusManagedTagManager(models.Manager):
    # a list of all CosinnusManagedTags
    _MANAGED_TAG_ALL_LIST_CACHE_KEY = 'cosinnus/core/portal/%d/managed_tags/all'  # portal_id
    # a dict of *both* mappings from int and slug to CosinnusManagedTags. contains duplicate tags!
    _MANAGED_TAG_DICT_CACHE_KEY = 'cosinnus/core/portal/%d/managed_tags/dict'  # portal_id

    def all_in_portal(self):
        """Returns all managed tags within the current portal only"""
        return self.get_queryset().filter(portal=CosinnusPortal().get_current())

    def all_in_portal_cached(self):
        """Returns a cached list of all managed tags within the current portal only"""
        cache_key = self._MANAGED_TAG_ALL_LIST_CACHE_KEY % CosinnusPortal().get_current().id
        all_tag_list = cache.get(cache_key)
        if all_tag_list is None:
            all_tag_list = list(self.all_in_portal())
            cache.set(cache_key, all_tag_list, settings.COSINNUS_MANAGED_TAG_CACHE_TIMEOUT)
        return all_tag_list

    def clear_cache(self):
        """Clears all cached managed tags"""
        cache.delete_many(
            [
                self._MANAGED_TAG_ALL_LIST_CACHE_KEY % CosinnusPortal().get_current().id,
                self._MANAGED_TAG_DICT_CACHE_KEY % CosinnusPortal().get_current().id,
            ]
        )

    def get_cached(self, pk_or_id_or_list):
        """Returns one or many cached tags, by any given combination of a single int pk,
        str slug or a list of both combinations.
        @param pk_or_id_or_list: int or str or list of int or strs to return tag by pk or slug"""

        if not pk_or_id_or_list:
            return [] if pk_or_id_or_list == [] else None
        single = isinstance(pk_or_id_or_list, six.string_types) or isinstance(pk_or_id_or_list, int)
        if single:
            pk_or_id_or_list = [pk_or_id_or_list]

        cache_key = self._MANAGED_TAG_DICT_CACHE_KEY % CosinnusPortal().get_current().id
        tag_dict = cache.get(cache_key)
        if tag_dict is None:
            all_tags = self.all_in_portal_cached()
            tag_dict = dict([(tag.id, tag) for tag in all_tags] + [(tag.slug, tag) for tag in all_tags])
            cache.set(cache_key, tag_dict, settings.COSINNUS_MANAGED_TAG_CACHE_TIMEOUT)

        tags = []
        for pk_or_slug in pk_or_id_or_list:
            tags.append(tag_dict.get(pk_or_slug, None))
        if single:
            return tags[0]
        return tags


class CosinnusManagedTagAssignmentQS(models.query.QuerySet):
    def tag_ids(self):
        """Returns all CosinnusManagedTag IDs from the set of assignements"""
        return self.distinct().values_list('managed_tag__id', flat=True)

    def tag_slugs(self):
        """Returns all CosinnusManagedTag slugs from the set of assignements"""
        return self.distinct().values_list('managed_tag__slug', flat=True)

    def approved(self):
        return self.filter(approved=True)


class CosinnusManagedTagAssignmentManager(models.Manager):
    def get_queryset(self):
        return CosinnusManagedTagAssignmentQS(self.model, using=self._db).select_related('managed_tag')

    def all_approved(self):
        return self.get_queryset().filter(approved=True)

    def get_for_model(self, model):
        model_type = ContentType.objects.get_for_model(model)
        return self.get_queryset().filter(content_type__pk=model_type.id)


class CosinnusManagedTagAssignment(models.Model):
    """The assignment intermediate-Model for CosinnusManagedTag"""

    managed_tag = models.ForeignKey('cosinnus.CosinnusManagedTag', related_name='assignments', on_delete=models.CASCADE)

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target_object = GenericForeignKey('content_type', 'object_id')

    assigners = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='managed_tag_assignments',
        blank=True,
        help_text=(
            'A list of people who suggested making this assignment. Can be empty, and can beignored once `approved` '
            'is True.'
        ),
    )
    approved = models.BooleanField(verbose_name=_('Approved'), default=False)
    last_modified = models.DateTimeField(verbose_name=_('Last modified'), editable=False, auto_now=True)

    objects = CosinnusManagedTagAssignmentManager()

    class Meta(object):
        app_label = 'cosinnus'
        unique_together = (('managed_tag', 'content_type', 'object_id'),)
        verbose_name = MANAGED_TAG_LABELS.ASSIGNMENT_VERBOSE_NAME
        verbose_name_plural = MANAGED_TAG_LABELS.ASSIGNMENT_VERBOSE_NAME_PLURAL

    def __str__(self):
        return (
            '<managed tag assignment: %(managed_tag)s, content_type: %(content_type)s, '
            'target_object_id: %(target_object_id)d>'
        ) % {
            'managed_tag': getattr(self, 'managed_tag', None),
            'content_type': getattr(self, 'content_type', None),
            'target_object_id': getattr(self, 'object_id', None),
        }

    @classmethod
    def update_assignments_for_object(cls, obj, tag_slugs_to_assign=None):
        """Will assign all given CosinnusManagedTags to the given object and remove existing assignments
        not contained in the given assignment list.
        @param obj: Any object to assign the managed tags to
        @param tag_slugs_to_assign: A list of slugs of CosinnusManagedTags. Only those slugs that actually
            exist will be assigned. If None or an empty list is given, all assignments will be removed from
            the object."""
        if not obj.pk:
            logger.error(
                'Could not save CosinnusManagedTags assignments: target object has not been saved yet!', extra={obj}
            )
            return
        content_type = ContentType.objects.get_for_model(obj._meta.model)
        assigned_slugs = list(
            cls.objects.filter(content_type=content_type, object_id=obj.id).values_list('managed_tag__slug', flat=True)
        )
        slugs_to_assign = [slug for slug in tag_slugs_to_assign if slug not in assigned_slugs]
        slugs_to_remove = [slug for slug in assigned_slugs if slug not in tag_slugs_to_assign]

        # remove unwanted existing tags
        to_remove_qs = cls.objects.filter(
            content_type=content_type, object_id=obj.id, managed_tag__slug__in=slugs_to_remove
        )
        slugs_removed = list(to_remove_qs.values_list('managed_tag__slug', flat=True))
        to_remove_qs.delete()

        # add wanted non-existant tags
        slugs_assigned = []
        for slug in slugs_to_assign:
            managed_tag = CosinnusManagedTag.objects.get_cached(slug)
            if managed_tag:
                approve = not bool(settings.COSINNUS_MANAGED_TAGS_USER_TAGS_REQUIRE_APPROVAL)
                cls.objects.create(
                    content_type=content_type, object_id=obj.id, managed_tag=managed_tag, approved=approve
                )
                slugs_assigned.append(slug)

        # send a signal for the tag assignment change
        slugs_removed = [slug for slug in slugs_removed if slug not in slugs_assigned]
        if slugs_assigned or slugs_removed:
            signals.managed_tags_changed.send(
                sender=cls, obj=obj, tag_slugs_added=slugs_assigned, tag_slugs_removed=slugs_removed
            )

    @classmethod
    def assign_managed_tag_to_object(cls, obj, tag_slug_to_assign):
        """Will assign a given CosinnusManagedTag to the given object and keep all other assigned tags.
        @param obj: Any object to assign the managed tag to
        @param tag_slug_to_assign: A slug of a CosinnusManagedTag. Only those slugs that actually
            exist will be assigned."""
        if not obj.pk:
            logger.error(
                'Could not save CosinnusManagedTags assignment: target object has not been saved yet!', extra={obj}
            )
            return
        content_type = ContentType.objects.get_for_model(obj._meta.model)
        assigned_slugs = list(
            cls.objects.filter(content_type=content_type, object_id=obj.id).values_list('managed_tag__slug', flat=True)
        )

        # add wanted non-assigned tag
        slugs_assigned = []
        if tag_slug_to_assign not in assigned_slugs:
            managed_tag = CosinnusManagedTag.objects.get_cached(tag_slug_to_assign)
            if managed_tag:
                approve = not bool(settings.COSINNUS_MANAGED_TAGS_USER_TAGS_REQUIRE_APPROVAL)
                cls.objects.create(
                    content_type=content_type, object_id=obj.id, managed_tag=managed_tag, approved=approve
                )
                slugs_assigned.append(tag_slug_to_assign)

        # send a signal for the tag assignment change
        if slugs_assigned:
            signals.managed_tags_changed.send(sender=cls, obj=obj, tag_slugs_added=slugs_assigned, tag_slugs_removed=[])


@six.python_2_unicode_compatible
class CosinnusManagedTagType(models.Model):
    # don't worry, the default Portal with id 1 is created in a datamigration
    # there was no other way to generate completely runnable migrations
    # (with a get_default function, or any other way)
    portal = models.ForeignKey(
        'cosinnus.CosinnusPortal',
        verbose_name=_('Portal'),
        related_name='managed_tag_types',
        null=False,
        blank=False,
        default=1,
        on_delete=models.CASCADE,
    )  # port_id 1 is created in a datamigration!

    name = models.CharField(_('Name'), max_length=250)
    prefix_label = models.CharField(
        _('Prefix label'),
        max_length=250,
        help_text=_('The label that will be prepended before Managed Tags of this type, instead of `name`'),
        blank=True,
        null=True,
    )
    color = models.CharField(
        _('Color'),
        max_length=10,
        validators=[MaxLengthValidator(7)],
        help_text=_('Optional color code (css hex value, with or without "#")'),
        blank=True,
        null=True,
    )

    class Meta(object):
        ordering = ('name',)
        verbose_name = MANAGED_TAG_LABELS.MANAGED_TAG_TYPE_NAME
        verbose_name_plural = MANAGED_TAG_LABELS.MANAGED_TAG_TYPE_NAME_PLURAL
        unique_together = (('name', 'portal'),)

    def __str__(self):
        return 'Type: %s (Portal %d)' % (self.name, self.portal_id)


@six.python_2_unicode_compatible
class CosinnusManagedTag(models.Model):
    # don't worry, the default Portal with id 1 is created in a datamigration
    # there was no other way to generate completely runnable migrations
    # (with a get_default function, or any other way)
    portal = models.ForeignKey(
        'cosinnus.CosinnusPortal',
        verbose_name=_('Portal'),
        related_name='managed_tags',
        null=False,
        blank=False,
        default=1,
        on_delete=models.CASCADE,
    )  # port_id 1 is created in a datamigration!

    type = models.ForeignKey(
        'cosinnus.CosinnusManagedTagType',
        verbose_name=MANAGED_TAG_LABELS.MANAGED_TAG_TYPE_NAME,
        related_name='managed_tags',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    name = models.CharField(_('Name'), max_length=250)
    slug = models.SlugField(
        _('Slug'),
        help_text=_(
            'Be extremely careful when changing this slug manually! There can be many side-effects '
            '(redirects breaking e.g.)!'
        ),
        max_length=250,
    )

    description = models.TextField(verbose_name=_('Short Description'), blank=True)

    image = models.ImageField(
        _('Image'), null=True, blank=True, upload_to=get_managed_tag_image_filename, max_length=250
    )
    url = models.URLField(_('URL'), max_length=200, blank=True, null=True, validators=[MaxLengthValidator(200)])

    paired_group = models.ForeignKey(
        settings.COSINNUS_GROUP_OBJECT_MODEL,
        verbose_name=_('Paired Group'),
        blank=True,
        null=True,
        related_name='paired_managed_tag',
        on_delete=models.SET_NULL,
        help_text=_('A paired group will automatically be joined by all users assigned to this object.'),
    )
    search_synonyms = models.TextField(
        _('Search Synonyms'),
        blank=True,
        null=True,
        help_text=_(
            'Comma-seperated list of phrases for which auto-complete matches, even partial, will return this object.'
        ),
    )

    created = models.DateTimeField(verbose_name=_('Created'), editable=False, auto_now_add=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Creator'),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='+',
    )
    last_modified = models.DateTimeField(verbose_name=_('Last modified'), editable=False, auto_now=True)

    objects = CosinnusManagedTagManager()

    # the label object, swappable per portal
    labels = MANAGED_TAG_LABELS

    class Meta(object):
        ordering = ('name',)
        verbose_name = MANAGED_TAG_LABELS.MANAGED_TAG_NAME
        verbose_name_plural = MANAGED_TAG_LABELS.MANAGED_TAG_NAME_PLURAL
        unique_together = (('slug', 'portal'),)

    def __str__(self):
        return '%s (Portal %d)' % (self.name, self.portal_id)

    def get_icon(self):
        """Returns the font-awesome icon specific to this object type"""
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
        self.clear_cache()

    def delete(self, *args, **kwargs):
        self.clear_cache()
        super(CosinnusManagedTag, self).delete(*args, **kwargs)

    def clear_cache(self):
        CosinnusManagedTag.objects.clear_cache()

    @property
    def sort_key(self):
        """A sort key with prefixed ManagedTagType name, usable as grouped sort key"""
        return ((self.type.name if self.type else 'zzzzzz__NO-TYPE') + ' - ' + self.name).lower()

    @property
    def image_url(self):
        return self.image.url if self.image else None

    @property
    def paired_group_url(self):
        return self.paired_group.get_absolute_url() if self.paired_group else None

    def get_image_thumbnail(self, size=(0, 80)):
        return image_thumbnail(self.image, size)

    def get_image_thumbnail_url(self, size=(0, 80)):
        return image_thumbnail_url(self.image, size)

    def get_absolute_url(self):
        """Returns the assigned url field's url"""
        return self.url or ''

    def get_user_management_url(self):
        return reverse('cosinnus:administration-users') + f'?managed_tag={self.id}'

    def get_search_url(self):
        """Returns the filtered search view for this tag"""
        return reverse('cosinnus:map') + f'?managed_tags={self.id}'

    @classmethod
    def create_managed_tag_and_paired_group(cls, name, creator, managed_tag_type=None, description=''):
        """Creates a managed tag if it doesn't exist and a paired group
        @param name: The name for both the managed tag and the paired group
        @param creator: user that is set as creator of the tag and group
        @param managed_tag_type: optional, the CosinnusManagedTagType for the tag
        @return: False if a managed tag of the given `name` already existed, the tag otherwise
        """
        tag_slug = slugify(name)
        existing_tag = get_object_or_None(CosinnusManagedTag, name__iexact=name, portal=CosinnusPortal().get_current())
        existing_tag_by_slug = get_object_or_None(
            CosinnusManagedTag, slug__iexact=tag_slug, portal=CosinnusPortal().get_current()
        )
        if existing_tag or existing_tag_by_slug:
            logger.info(
                (
                    '`create_managed_tag_and_paired_group` Did not create a new managed tag because an existing tag '
                    'has the same name or slug'
                ),
                extra={'new_tag_name': name},
            )
            return existing_tag or existing_tag_by_slug

        # create group
        try:
            from cosinnus.models.group_extra import CosinnusSociety

            group_name = f'{settings.COSINNUS_MANAGED_TAGS_PAIRED_GROUPS_PREFIX}{name}'
            if creator is None or not creator.is_authenticated:
                paired_group = CosinnusSociety.create_group_without_member(group_name)
            else:
                paired_group = CosinnusSociety.create_group_for_user(group_name, creator)

        except Exception as e:
            logger.error(
                'Error when creating a new managed tag, could not create paired group, but continuing tag creation!',
                extra={'exception': e},
            )
            if settings.DEBUG:
                raise

        # create tag
        try:
            managed_tag = CosinnusManagedTag.objects.create(
                name=name,
                slug=tag_slug,
                creator=creator,
                type=managed_tag_type,
                paired_group=paired_group,
                portal=CosinnusPortal().get_current(),
                description=description,
            )
        except Exception as e:
            logger.error('Error when creating a new managed tag, during paired group creation', extra={'exception': e})
            if settings.DEBUG:
                raise
            return False
        return managed_tag


class CosinnusManagedTagAssignmentModelMixin(object):
    """Mixin for models that can have CosinnusManagedTagAssignments assigned.
    You still need to add
    `managed_tag_assignments = GenericRelation('cosinnus.CosinnusManagedTagAssignment')`
    to your model."""

    def get_managed_tag_ids(self):
        """Returns all ids of approved assigned managed tags for this object"""
        return list(self.managed_tag_assignments.all().filter(approved=True).values_list('managed_tag', flat=True))

    def get_managed_tag_slugs(self):
        """Returns all slugs of approved assigned managed tags for this object"""
        return list(
            self.managed_tag_assignments.all().filter(approved=True).values_list('managed_tag__slug', flat=True)
        )

    def get_managed_tags(self):
        """Returns all approved assigned managed tags for this object"""
        tag_ids = self.get_managed_tag_ids()
        return CosinnusManagedTag.objects.get_cached(list(tag_ids))
