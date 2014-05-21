# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from taggit.managers import TaggableManager

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusGroup
from cosinnus.utils.functions import unique_aware_slugify


class LocationModelMixin(models.Model):
    location_place = models.CharField(max_length=255, default='', blank=True)

    class Meta:
        abstract = True


class PeopleModelMixin(models.Model):
    people_name = models.CharField(max_length=255, default='', blank=True)

    class Meta:
        abstract = True


class PublicModelMixin(models.Model):
    public = models.BooleanField(_('Public'), default=False, blank=True)

    class Meta:
        abstract = True


@python_2_unicode_compatible
class BaseTagObject(models.Model):

    VISIBILITY_USER = 0
    VISIBILITY_GROUP = 1
    VISIBILITY_ALL = 2

    #: Choices for :attr:`visibility`: ``(int, str)``
    VISIBILITY_CHOICES = (
        (VISIBILITY_USER, _('User')),
        (VISIBILITY_GROUP, _('Group')),
        (VISIBILITY_ALL, _('All')),
    )

    group = models.ForeignKey(CosinnusGroup, verbose_name=_('Group'),
        related_name='+', null=True)

    persons = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True,
        null=True, verbose_name=_('Persons'), related_name='+')
    visibility = models.PositiveSmallIntegerField(_('Permissions'), blank=True,
        default=VISIBILITY_GROUP, choices=VISIBILITY_CHOICES)

    class Meta:
        abstract = True

    def __str__(self):
        return "Tag object {0}".format(self.pk)


class TagObject(LocationModelMixin, PeopleModelMixin, PublicModelMixin,
                BaseTagObject):

    class Meta:
        app_label = 'cosinnus'
        swappable = 'COSINNUS_TAG_OBJECT_MODEL'


@python_2_unicode_compatible
class AttachedObject(models.Model):
    """
    A generic object to serve as attachable object connector for all cosinnus
    objects.
    """

    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    target_object = generic.GenericForeignKey('content_type', 'object_id')

    class Meta:
        app_label = 'cosinnus'
        ordering = ('content_type',)
        unique_together = (('content_type', 'object_id'),)
        verbose_name = _('Attached object')
        verbose_name_plural = _('Attached objects')

    def __str__(self):
        return '<attach: %s::%s>' % (self.content_type, self.object_id)

    @property
    def model_name(self):
        """
        The model name used in the cosinnus attached file configurations, e.g.:
        `'cosinnus_file.FileEntry'`
        """
        if not hasattr(self, '_model_name'):
            ct = self.content_type
            self._model_name = '%s.%s' % (ct.app_label, ct.model_class().__name__)
        return self._model_name


@python_2_unicode_compatible
class BaseTaggableObjectModel(models.Model):
    """
    Represents the base for all cosinnus main models. Each inheriting model
    has a set of simple ``tags`` which are just strings. Additionally each
    model has a ``media_tag`` that refers to all general tags like a location,
    people and so on.
    """

    tags = TaggableManager(_('Tags'), blank=True)
    media_tag = models.OneToOneField(settings.COSINNUS_TAG_OBJECT_MODEL,
        blank=True, null=True, on_delete=models.PROTECT)

    attached_objects = models.ManyToManyField(AttachedObject, blank=True, null=True)

    group = models.ForeignKey(CosinnusGroup, verbose_name=_('Group'),
        related_name='%(app_label)s_%(class)s_set', on_delete=models.PROTECT)

    title = models.CharField(_('Title'), max_length=255)
    slug = models.SlugField(max_length=55, blank=True)  # human readable part is 50 chars

    creator = models.ForeignKey(settings.AUTH_USER_MODEL,
        verbose_name=_('Creator'),
        on_delete=models.PROTECT,
        null=True,
        related_name='%(app_label)s_%(class)s_set')
    created = models.DateTimeField(
        verbose_name=_('Created'),
        editable=False,
        default=now,
        auto_now_add=True)

    class Meta:
        abstract = True
        unique_together = (('group', 'slug'),)

    def __str__(self):
        return self.title

    def __repr__(self):
        return "<tagged object {0} {1} (ID: {2})>".format(
            self.__class__.__name__, self.title, self.pk)

    def save(self, *args, **kwargs):
        unique_aware_slugify(self, 'title', 'slug', group=self.group)
        super(BaseTaggableObjectModel, self).save(*args, **kwargs)


class BaseHierarchicalTaggableObjectModel(BaseTaggableObjectModel):
    """
    Represents the base for hierarchical cosinnus models.
    """
    is_container = models.BooleanField(
        blank=False, null=False, default=False, editable=True)
    path = models.CharField(_('Path'),
        blank=False, null=False, default='/', max_length=100)

    class Meta(BaseTaggableObjectModel.Meta):
        abstract = True

    def __str__(self):
        return '%s (%s)' % (self.title, self.path)

    def save(self, *args, **kwargs):
        if self.path[-1] != '/':
            self.path += '/'
        super(BaseHierarchicalTaggableObjectModel, self).save(*args, **kwargs)
    
    @property
    def container(self):
        """ Returns the hierarchical object's parent container or None if root or the object doesn't exist """
        if self.path == '/':
            return None
        if self.is_container:
            # go to parent folder path
            parentpath, _, _= self.path[:-1].rpartition('/')
            path = parentpath + '/'
        else:
            path = self.path
        
        qs = self.__class__.objects.all().filter(Q(group=self.group) & Q(is_container=True) & Q(path=path))
        first_list = list(qs[:1])
        if first_list:
            return first_list[0]
        return None

def ensure_container(sender, **kwargs):
    """ Creates a root container instance for all hierarchical objects in a newly created group """
    created = kwargs.get('created', False)
    if created:
        for model_class in BaseHierarchicalTaggableObjectModel.__subclasses__():
            if not model_class._meta.abstract:
                model_class.objects.create(group=kwargs.get('instance'), slug='_root_', title='_root_', path='/', is_container=True)
                
post_save.connect(ensure_container, sender=CosinnusGroup)


def get_tag_object_model():
    """
    Return the cosinnus tag object model that is defined in
    :data:`settings.COSINNUS_TAG_OBJECT_MODEL`
    """
    from django.core.exceptions import ImproperlyConfigured
    from django.db.models import get_model
    from cosinnus.conf import settings

    try:
        app_label, model_name = settings.COSINNUS_TAG_OBJECT_MODEL.split('.')
    except ValueError:
        raise ImproperlyConfigured("COSINNUS_TAG_OBJECT_MODEL must be of the form 'app_label.model_name'")
    tag_model = get_model(app_label, model_name)
    if tag_model is None:
        raise ImproperlyConfigured("COSINNUS_TAG_OBJECT_MODEL refers to model '%s' that has not been installed" %
            settings.COSINNUS_TAG_OBJECT_MODEL)
    return tag_model


def get_tagged_object_filter_for_user(user):
    q = Q(group__public=True)  # All tagged objects in public groups
    q |= Q(media_tag__visibility=BaseTagObject.VISIBILITY_ALL)  # All public tagged objects
    if user.is_authenticated():
        gids = CosinnusGroup.objects.get_for_user_pks(user)
        q |= Q(  # all tagged objects in groups the user is a member of
            media_tag__visibility=BaseTagObject.VISIBILITY_GROUP,
            group_id__in=gids
        )
        q |= Q(  # all tagged objects the user is explicitly a linked to
            media_tag__visibility=BaseTagObject.VISIBILITY_USER,
            media_tag__persons__id=user.id
        )
    return q
