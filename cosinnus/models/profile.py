# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six
import django

from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.signals import post_save, class_prepared
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from easy_thumbnails.files import get_thumbnailer
from easy_thumbnails.exceptions import InvalidImageFormatError
from jsonfield import JSONField

from cosinnus.conf import settings
from cosinnus.utils.files import get_avatar_filename
from cosinnus.models.group import CosinnusGroup
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.core import signals


class BaseUserProfileManager(models.Manager):
    use_for_related_fields = True

    def get_for_user(self, user):
        """
        Return the user profile for a given user.

        :param user: Either an int which defines the user's primary key or a
            model instance.
        :return: The user profile for the given model. The concrete subclass of
            ``BaseUserProfile`` as defined by ``COSINNUS_USER_PROFILE_MODEL``.
        :raise TypeError: If user is neither an int nor a model.
        """
        if isinstance(user, int):
            return self.get(user_id=user)
        if isinstance(user, models.Model):
            try:
                profile = self.get(user_id=user.id)
            except get_user_profile_model().DoesNotExist:
                profile = self.create(user_id=user.id)
            return profile
        raise TypeError('user must be of type int or Model but is %s' % type(user))


@python_2_unicode_compatible
class BaseUserProfile(models.Model):
    """
    This is a base user profile used within cosinnus. To use it, create your
    own model inheriting from this model.

    .. code-block:: python

        from django.db import models
        from cosinnus.models.profile import BaseUserProfile

        class MyUserProfile(BaseUserProfile):
            myfield = models.CharField('myfield', max_length=10)

    Additionally set the settings variable ``COSINNUS_USER_PROFILE_MODEL`` to
    the dotted model path (myapp.MyUserProfile). This works the same way as
    Django's custom user model.

    To get a user's profile e.g in a view use the ``get_for_user()`` method
    on the manager:

    .. code-block:: python

        from myapp.models import MyUserProfile

        def myview(request):
            user = request.user
            profile = MyUserProfile.objects.get_for_user(user)
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, editable=False,
        related_name='cosinnus_profile')

    objects = BaseUserProfileManager()

    SKIP_FIELDS = ('id', 'user', 'user_id', 'media_tag', 'media_tag_id', 'settings')

    class Meta:
        abstract = True

    def __str__(self):
        return six.text_type(self.user)

    def save(self, *args, **kwargs):
        try:
            existing = self._default_manager.get(user=self.user)
            # workaround for http://goo.gl/4I8Ok
            self.id = existing.id  # force update instead of insert
        except ObjectDoesNotExist:
            pass
        super(BaseUserProfile, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return group_aware_reverse('cosinnus:profile-detail', kwargs={'username': self.user.username})

    @classmethod
    def get_optional_fieldnames(cls):
        """
        Iterates over all fields defined in the user profile and returns a list
        of field names.

        The list will only contain those fields not listed in ``SKIP_FIELDS``.
        """
        return list(set(cls._meta.get_all_field_names()) - set(cls.SKIP_FIELDS))

    def get_optional_fields(self):
        """
        Iterates over all fields defined in the user profile and returns a list
        of dicts with the keys ``name`` and ``value``.

        The list will only contain those fields not listed in ``SKIP_FIELDS``.
        """
        all_fields = self._meta.get_all_field_names()
        optional_fields = []
        for name in all_fields:
            if name in self.SKIP_FIELDS:
                continue
            value = getattr(self, name)
            if value:
                field = self._meta.get_field_by_name(name)[0]
                optional_fields.append({
                    'name': field.verbose_name,
                    'value': value,
                })
        return optional_fields
    
    @property
    def cosinnus_groups(self):
        """ Returns all groups this user is a member or admin of """
        return CosinnusGroup.objects.get_for_user(self.user)

class UserProfile(BaseUserProfile):
    
    class Meta:
        app_label = 'cosinnus'
        swappable = 'COSINNUS_USER_PROFILE_MODEL'
    
    avatar = models.ImageField(_("Avatar"), null=True, blank=True,
        upload_to=get_avatar_filename)
    description = models.TextField(verbose_name=_('Description'), blank=True, null=True)
    media_tag = models.OneToOneField(settings.COSINNUS_TAG_OBJECT_MODEL,
        blank=True, null=True, editable=False, on_delete=models.SET_NULL)
    website = models.URLField(_('Website'), max_length=100, blank=True, null=True)
    settings = JSONField(default={})

    @property
    def avatar_url(self):
        return self.avatar.url if self.avatar else None

    def get_avatar_thumbnail(self, size=(80, 80)):
        if not self.avatar:
            return None

        thumbnails = getattr(self, '_avatar_thumbnails', {})
        if size not in thumbnails:
            thumbnailer = get_thumbnailer(self.avatar)
            try:
                thumbnails[size] = thumbnailer.get_thumbnail({
                    'crop': True,
                    'size': size,
                })
            except InvalidImageFormatError:
                if settings.DEBUG:
                    raise
            setattr(self, '_avatar_thumbnails', thumbnails)
        return thumbnails.get(size, None)

    def get_avatar_thumbnail_url(self, size=(80, 80)):
        tn = self.get_avatar_thumbnail(size)
        return tn.url if tn else None
    
    def media_tag_object(self):
        key = '_media_tag_cache'
        if not hasattr(self, key):
            setattr(self, key, self.media_tag)
        return getattr(self, key)
    
    def save(self, *args, **kwargs):
        created = bool(self.pk is None)
        # sanity check for missing media_tag:
        if not self.media_tag:
            from cosinnus.models.tagged import get_tag_object_model
            media_tag = get_tag_object_model()._default_manager.create()
            self.media_tag = media_tag
        super(UserProfile, self).save(*args, **kwargs)
        
        if created:
            # send creation signal
            signals.userprofile_ceated.send(sender=self, profile=self)
        


def get_user_profile_model():
    "Return the cosinnus user profile model that is active in this project"
    from django.core.exceptions import ImproperlyConfigured
    from django.db.models import get_model
    from cosinnus.conf import settings

    try:
        app_label, model_name = settings.COSINNUS_USER_PROFILE_MODEL.split('.')
    except ValueError:
        raise ImproperlyConfigured("COSINNUS_USER_PROFILE_MODEL must be of the form 'app_label.model_name'")
    user_profile_model = get_model(app_label, model_name)
    if user_profile_model is None:
        raise ImproperlyConfigured("COSINNUS_USER_PROFILE_MODEL refers to model '%s' that has not been installed" %
            settings.COSINNUS_USER_PROFILE_MODEL)
    return user_profile_model


def create_user_profile(sender, instance, created, **kwargs):
    """
    Creates (if necessary) or gets a new user profile for the given user
    instance.
    """
    upm = get_user_profile_model()
    upm.objects.get_or_create(user=instance)


if django.VERSION[:2] < (1, 7):

    def setup_user_profile_signal(sender, **kwargs):
        name = '%s.%s' % (sender._meta.app_label, sender._meta.object_name)
        if name == settings.AUTH_USER_MODEL:
            post_save.connect(create_user_profile, sender=sender,
                dispatch_uid='cosinnus_user_profile_post_save')

    try:
        from django.contrib.auth import get_user_model
        post_save.connect(create_user_profile, sender=get_user_model(),
                dispatch_uid='cosinnus_user_profile_post_save')
    except:
        if settings.DEBUG:
            from traceback import print_exc
            print_exc()
        class_prepared.connect(setup_user_profile_signal)
else:
    # Django >= 1.7 supports lazy signal registration
    # https://github.com/django/django/commit/eb38257e51
    post_save.connect(create_user_profile, sender=settings.AUTH_USER_MODEL,
        dispatch_uid='cosinnus_user_profile_post_save')
