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
from cosinnus.models.group import CosinnusGroup, CosinnusPortal
from cosinnus.utils.functions import unique_aware_slugify,\
    clean_single_line_text
from cosinnus.models.widget import WidgetConfig
from cosinnus.core.registries.widgets import widget_registry
from django.utils.functional import cached_property
from django.core.exceptions import ImproperlyConfigured
from cosinnus import cosinnus_notifications
from cosinnus.core.registries.group_models import group_model_registry


from osm_field.fields import OSMField, LatitudeField, LongitudeField
from cosinnus.utils.lanugages import MultiLanguageFieldMagicMixin
from cosinnus.core.registries import app_registry
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from cosinnus.utils.group import get_cosinnus_group_model




class PeopleModelMixin(models.Model):
    people_name = models.CharField(max_length=255, default='', blank=True)

    class Meta:
        abstract = True


class PublicModelMixin(models.Model):
    public = models.BooleanField(_('Public'), default=False, blank=True)

    class Meta:
        abstract = True


@python_2_unicode_compatible
class CosinnusBaseCategory(models.Model):
    
    class Meta:
        abstract = True
    
    name = models.CharField(_('Name'), max_length=250)
    name_en = models.CharField(_('Name (EN)'), max_length=250, blank=True, null=True)
    name_ru = models.CharField(_('Name (RU)'), max_length=250, blank=True, null=True)
    name_uk = models.CharField(_('Name (UK)'), max_length=250, blank=True, null=True)
    
    @property
    def display_name(self):
        return self['name']
    
    def __str__(self):
        return '%s' % self.display_name


class CosinnusTopicCategory(MultiLanguageFieldMagicMixin, CosinnusBaseCategory):
    pass


@python_2_unicode_compatible
class BaseTagObject(models.Model):

    VISIBILITY_USER = 0 # for Users, this setting means: "Only Group Members can see me"
    VISIBILITY_GROUP = 1 # for Users, this setting means: "Only Logged in Users can see me"
    VISIBILITY_ALL = 2 # for Users, this setting means: "Everyone can see me"

    #: Choices for :attr:`visibility`: ``(int, str)``
    # Empty first choice must be included for select2 placeholder compatibility!
    VISIBILITY_CHOICES = (
        ('', ''),
        (VISIBILITY_USER, _('Only me')),  
        (VISIBILITY_GROUP, _('Team members only')), 
        (VISIBILITY_ALL, _('Public (visible without login)')), 
    )

    group = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL, verbose_name=_('Team'),
        related_name='+', null=True, on_delete=models.CASCADE)

    persons = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True,
        null=True, verbose_name=_('Persons'), related_name='+')
    
    tags = TaggableManager(_('Tags'), blank=True)

    visibility = models.PositiveSmallIntegerField(_('Permissions'), blank=True,
        default=VISIBILITY_GROUP, choices=VISIBILITY_CHOICES)
    
    
    #: Choices for :attr:`approach`: ``(str, str)``
    # Empty first choice must be included for select2 placeholder compatibility!
    APPROACH_CHOICES = (
        ('',''),
        ('zivilgesellschaft', 'Zivilgesellschaft'),
        ('politik', 'Politik'),
        ('forschung', 'Forschung'),
        ('unternehmen', 'Unternehmen'),
    )

    location = OSMField(_('Location'), blank=True, null=True)
    location_lat = LatitudeField(_('Latitude'), blank=True, null=True)
    location_lon = LongitudeField(_('Longitude'), blank=True, null=True)
    
    place = models.CharField(_('Place'), max_length=100, default='',
        blank=True)

    valid_start = models.DateTimeField(_('Valid from'), blank=True, null=True)
    valid_end = models.DateTimeField(_('Valid to'), blank=True, null=True)

    approach = models.CharField(_('Approach'), blank=True, null=True,
        choices=APPROACH_CHOICES, max_length=255)

    #: Choices for :attr:`topics`: ``(int, str)``
    # Empty first choice must be included for select2 placeholder compatibility!
    TOPIC_CHOICES = getattr(settings, 'COSINNUS_TOPIC_CHOICES', [])

    topics = models.CommaSeparatedIntegerField(_('Topics'), blank=True,
        null=True, max_length=255)  # We cannot add choices here as this would 
                                    # fail validation
    text_topics = models.ManyToManyField(CosinnusTopicCategory, verbose_name=_('Text Topics'), 
        related_name='tagged_objects', blank=True, null=True)
    
                                    
    likes = models.PositiveSmallIntegerField(_('Likes'), blank=True, default=0)
    likers = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True,
        null=True, related_name='likes+')  # no reverse relation on model
    
    def save(self, *args, **kwargs):
        # update like count
        if self.pk:
            self.likes = self.likers.count()
        super(BaseTagObject, self).save(*args, **kwargs)
    
    @property
    def get_topics_display(self):
        return ', '.join(self.get_topics())
    
    @property
    def get_topics(self):
        ret = []
        if self.topics:
            m = dict(BaseTagObject.TOPIC_CHOICES)
            for i in map(lambda x: int(x.strip()), [topic for topic in self.topics.split(',') if topic]):
                t = m.get(i, None)
                if t:
                    ret.append(t)
        return ret
    
    @property
    def location_url(self):
        if not self.location_lat or not self.location_lon:
            return None
        return 'http://www.openstreetmap.org/?mlat=%s&mlon=%s&zoom=15&layers=M' % (self.location_lat, self.location_lon)
    
    class Meta:
        abstract = True

    def __str__(self):
        return "Tag object {0}".format(self.pk)


class TagObject(BaseTagObject):

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


class AttachableObjectModel(models.Model):
    
    class Meta:
        abstract = True
    
    attached_objects = models.ManyToManyField(AttachedObject, blank=True, null=True)
    
    @cached_property
    def attached_image(self):
        """ Return the first image file attached to the event as the event's image """
        for attached_file in self.attached_objects.all():
            if attached_file.model_name == "cosinnus_file.FileEntry" and attached_file.target_object is not None and \
                        attached_file.target_object.is_image:
                return attached_file.target_object
        return None
    
    @cached_property
    def attached_images(self):
        """ Return the all image files attached to the event"""
        images = []
        for attached_file in self.attached_objects.all():
            if attached_file.model_name == "cosinnus_file.FileEntry" and attached_file.target_object is not None and \
                         attached_file.target_object.is_image:
                images.append(attached_file.target_object)
        return images
    

@python_2_unicode_compatible
class BaseTaggableObjectModel(AttachableObjectModel):
    """
    Represents the base for all cosinnus main models. Each inheriting model
    has a set of simple ``tags`` which are just strings. Additionally each
    model has a ``media_tag`` that refers to all general tags like a location,
    people and so on.
    """

    media_tag = models.OneToOneField(settings.COSINNUS_TAG_OBJECT_MODEL,
        blank=True, null=True, on_delete=models.SET_NULL)

    group = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL, verbose_name=_('Team'),
        related_name='%(app_label)s_%(class)s_set', on_delete=models.CASCADE)

    title = models.CharField(_('Title'), max_length=255)
    slug = models.SlugField(max_length=55, blank=True)  # human readable part is 50 chars

    creator = models.ForeignKey(settings.AUTH_USER_MODEL,
        verbose_name=_('Creator'),
        on_delete=models.CASCADE,
        null=True,
        related_name='%(app_label)s_%(class)s_set')
    created = models.DateTimeField(
        verbose_name=_('Created'),
        editable=False,
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
        created = bool(self.pk) == False
        unique_aware_slugify(self, 'title', 'slug', group=self.group)
        self.title = clean_single_line_text(self.title)
        if hasattr(self, '_media_tag_cache'):
            del self._media_tag_cache
        super(BaseTaggableObjectModel, self).save(*args, **kwargs)
        if not getattr(self, 'media_tag', None):
            self.media_tag = get_tag_object_model().objects.create()
            self.save()
        if created:
            pass
    
    def on_save_added_tagged_persons(self, set_users):
        """ Called by the taggable form whenever this object is saved and -new- persons
            have been added as tagged! 
            This can be overridden in specific TaggableObjects for a more specific notification email message.
            Just add extra={'mail_template':'<your_template>', 'subject_template':'<your_template>'} """
        # exclude creator from audience always
        set_users -= set([self.creator])
        cosinnus_notifications.user_tagged_in_object.send(sender=self, user=self.creator, obj=self, audience=list(set_users))
            

    def media_tag_object(self):
        key = '_media_tag_cache'
        if not hasattr(self, key):
            if self.media_tag_id is None:
                setattr(self, key, self.group.media_tag)
            else:
                setattr(self, key, self.media_tag)
        return getattr(self, key)
    
    @property
    def sort_key(self):
        """ The main property on which this object model is sorted """
        if not self.created:
            return now()
        return self.created
    
    def grant_extra_read_permissions(self, user):
        """ An overridable check for whether this object grants certain users read permissions
            even though by general rules that user couldn't read the object.
            
            @param user: The user to check for extra permissions for """
        return False
    
    def grant_extra_write_permissions(self, user, **kwargs):
        """ An overridable check for whether this object grants certain users write permissions
            even though by general rules that user couldn't write the object.
            
            @param user: The user to check for extra permissions for """
        return False
    
    def get_delete_url(self):
        """ Similar to get_absolute_url, this returns the URL for this object's implemented delete view.
            Needs to be set by a specific implementation of BaseTaggableObjectModel """
        raise ImproperlyConfigured("The get_delete_url function must be implemented for model '%s'" % self.__class__)
    
    def get_cosinnus_app_name(self):
        return app_registry.get_name(self.__class__.__module__.split('.')[0])
    
    def render_additional_notification_content_rows(self):
        """ Used when rendering email notifications for an object. Any list of html strings returned here
            will be added, on row each, after the object_text of the notification object.
            Note: use mark_safe on the html strings if you do not wish them to be escaped!
            @return: An array of HTML strings or [] """
        content_snippets = []
        tag_object = self.media_tag
        if tag_object.location and tag_object.location_url:
            location_html = render_to_string('cosinnus/html_mail/content_snippets/tagged_location.html', 
                                             {'tag_object': tag_object, 'domain': CosinnusPortal.get_current().get_domain()})
            content_snippets.append(mark_safe(location_html))
        return content_snippets


class BaseHierarchicalTaggableObjectModel(BaseTaggableObjectModel):
    """
    Represents the base for hierarchical cosinnus models.
    """
    is_container = models.BooleanField(
        blank=False, null=False, default=False, editable=True)
    special_type = models.CharField(
        help_text='A special folder appears differently on the site and cannot be deleted by users',
        blank=True, null=True, default=None, editable=False, max_length=8)
    path = models.CharField(_('Path'),
        blank=False, null=False, default='/', max_length=250)

    class Meta(BaseTaggableObjectModel.Meta):
        abstract = True

    def __str__(self):
        return '%s (%s)' % (self.title, self.path)

    def save(self, *args, **kwargs):
        if self.path[-1] != '/':
            self.path += '/'
        super(BaseHierarchicalTaggableObjectModel, self).save(*args, **kwargs)
    
    @cached_property
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
        
        # the folder class is always only one sub-model below BaseHierarchicalTaggableObjectModel.
        folder_class = self.__class__
        while not BaseHierarchicalTaggableObjectModel in folder_class.__bases__:
            folder_class = folder_class.__bases__[0]
        
        qs = folder_class.objects.all().filter(Q(group=self.group) & Q(is_container=True) & Q(path=path))
        first_list = list(qs[:1])
        if first_list:
            return first_list[0]
        return None


@python_2_unicode_compatible
class BaseTaggableObjectReflection(models.Model):
    """ Used as an additional link of a BaseTaggableObject into other Groups than its parent group.
        Can be used to "symbolically link" an object into another group, to display it there as well,
        while it still is retained in its original group. """
        
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    reflected_object = generic.GenericForeignKey('content_type', 'object_id')
    
    group = models.ForeignKey(settings.COSINNUS_GROUP_OBJECT_MODEL,
        on_delete=models.CASCADE, 
        related_name='reflected_objects')
    
    creator = models.ForeignKey(settings.AUTH_USER_MODEL,
        verbose_name=_('Creator'),
        on_delete=models.CASCADE,
        related_name='+')

    class Meta:
        app_label = 'cosinnus'
        ordering = ('content_type',)
        unique_together = (('content_type', 'object_id', 'group'),)
        verbose_name = _('Reflected Object')
        verbose_name_plural = _('Reflected Objects')

    def __str__(self):
        return '<reflect: %s::%s::%s>' % (self.content_type, self.object_id, self.group.slug)

    @property
    def model_name(self):
        """
        The model name of the reflected object, e.g.: `'cosinnus_event.Event'`
        """
        if not hasattr(self, '_model_name'):
            ct = self.content_type
            self._model_name = '%s.%s' % (ct.app_label, ct.model_class().__name__)
        return self._model_name
    
    @classmethod
    def get_objects_for_group(cls, model_class, group):
        """ Will return a queryset of class `model_class` that are reflected into the given group """
        ct = ContentType.objects.get_for_model(model_class)
        ids = cls.objects.filter(content_type=ct, group=group).values_list('id', flat=True)
        return model_class.objects.filter(id__in=ids)

    @classmethod
    def get_group_ids_for_object(cls, obj):
        """ Will return a list of ids of CosinnusBaseGroup that the given object is being reflected into. """
        ct = ContentType.objects.get_for_model(obj._meta.model)
        group_ids = cls.objects.filter(content_type=ct, object_id=obj.id).values_list('group_id', flat=True)
        return group_ids
    
    @classmethod
    def get_groups_for_object(cls, obj):
        """ Will return a queryset of all CosinnusBaseGroup (not projects or societies!) that the 
            given object is being reflected into. """
        group_ids = cls.get_group_ids_for_object(obj)
        return get_cosinnus_group_model().objects.get_cached(pks=group_ids)


def ensure_container(sender, **kwargs):
    """ Creates a root container instance for all hierarchical objects in a newly created group """
    created = kwargs.get('created', False)
    if created:
        for model_class in BaseHierarchicalTaggableObjectModel.__subclasses__():
            if not model_class._meta.abstract:
                model_class.objects.create(group=kwargs.get('instance'), slug='_root_', title='_root_', path='/', is_container=True)

    

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


