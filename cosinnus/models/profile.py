# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six
import django

from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.signals import post_save, class_prepared
from django.utils.encoding import python_2_unicode_compatible, force_text
from django.utils.translation import ugettext_lazy as _

from easy_thumbnails.files import get_thumbnailer
from easy_thumbnails.exceptions import InvalidImageFormatError
from jsonfield import JSONField

from cosinnus.conf import settings
from cosinnus.conf import settings as cosinnus_settings
from cosinnus.utils.files import get_avatar_filename
from cosinnus.models.group import CosinnusGroup, CosinnusPortal
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.core import signals
from cosinnus.utils.group import get_cosinnus_group_model
from django.contrib.staticfiles.templatetags.staticfiles import static
from cosinnus.views.facebook_integration import FacebookIntegrationUserProfileMixin
import copy
from cosinnus.core.mail import send_mail_or_fail_threaded
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from cosinnus.utils.user import get_newly_registered_user_email

# if a user profile has this settings, its user has not yet confirmed a new email
# address and this long is bound to his old email (or to a scrambled, unusable one if they just registered)
PROFILE_SETTING_EMAIL_TO_VERIFY = 'email_to_verify'
PROFILE_SETTING_EMAIL_VERFICIATION_TOKEN = 'email_verification_pwd'
# a list of urls to redirect the user to on next page hit (only first in list), enforced by middleware
PROFILE_SETTING_REDIRECT_NEXT_VISIT = 'redirect_next'
# first login datetime, used to determine if user first logged in
PROFILE_SETTING_FIRST_LOGIN = 'first_login'


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
class BaseUserProfile(FacebookIntegrationUserProfileMixin, models.Model):
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
    # if this or any extending profile models define additional username fields,
    # such as middle name, list the field names here
    ADDITIONAL_USERNAME_FIELDS = []
    
    user = models.OneToOneField(settings.AUTH_USER_MODEL, editable=False,
        related_name='cosinnus_profile')
    
    avatar = models.ImageField(_("Avatar"), null=True, blank=True,
        upload_to=get_avatar_filename)
    description = models.TextField(verbose_name=_('Description'), blank=True, null=True)
    media_tag = models.OneToOneField(settings.COSINNUS_TAG_OBJECT_MODEL,
        blank=True, null=True, editable=False, on_delete=models.SET_NULL)
    website = models.URLField(_('Website'), max_length=100, blank=True, null=True)
    language = models.CharField(_('Language'), max_length=2,
        choices=settings.LANGUAGES, default='de')
    
    settings = JSONField(default={})

    objects = BaseUserProfileManager()

    SKIP_FIELDS = ['id', 'user', 'user_id', 'media_tag', 'media_tag_id', 'settings']\
                    + getattr(cosinnus_settings, 'COSINNUS_USER_PROFILE_ADDITIONAL_FORM_SKIP_FIELDS', [])
                    
    _settings = None                
    
    class Meta:
        abstract = True
        
    def __init__(self, *args, **kwargs):
        super(BaseUserProfile, self).__init__(*args, **kwargs)
        self._settings = copy.deepcopy(self.settings)
        
    def __str__(self):
        return six.text_type(self.user)
    
    def get_full_name(self):
        return self.user.get_full_name()
    
    def get_extended_full_name(self):
        """ Stub extended username, including possible titles, middle names, etc """
        return self.get_full_name()
    
    def save(self, *args, **kwargs):
        created = bool(self.pk is None)
        # sanity check for missing media_tag:
        if not self.media_tag:
            from cosinnus.models.tagged import get_tag_object_model
            media_tag = get_tag_object_model()._default_manager.create()
            self.media_tag = media_tag
            
        try:
            existing = self._default_manager.get(user=self.user)
            # workaround for http://goo.gl/4I8Ok
            self.id = existing.id  # force update instead of insert
        except ObjectDoesNotExist:
            pass
        super(BaseUserProfile, self).save(*args, **kwargs)
        
        if created:
            # send creation signal
            signals.userprofile_ceated.send(sender=self, profile=self)
        
        # send a copy of the ToS to the User via email?
        if settings.COSINNUS_SEND_TOS_AFTER_USER_REGISTRATION and self.user and self.user.email:
            if self.settings.get('tos_accepted', False) and not self._settings.get('tos_accepted', False):
                tos_content = mark_safe(strip_tags(render_to_string('nutzungsbedingungen_content.html')))
                data = {
                    'user': self.user,
                    'site_name': _(settings.COSINNUS_BASE_PAGE_TITLE_TRANS),
                    'domain_url': CosinnusPortal.get_current().get_domain(),
                    'tos_content': tos_content,
                }
                subj_user = '%s - %s' % (_('Terms of Service'), data['site_name'])
                send_mail_or_fail_threaded(get_newly_registered_user_email(self.user), subj_user, 'cosinnus/mail/user_terms_of_services.html', data)

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
        return get_cosinnus_group_model().objects.get_for_user(self.user)
    
    @property
    def cosinnus_groups_pks(self):
        """ Returns all group ids this user is a member or admin of """
        return get_cosinnus_group_model().objects.get_for_user_pks(self.user)
    
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
                    'upscale': True,
                    'size': size,
                })
            except InvalidImageFormatError:
                if settings.DEBUG:
                    raise
            setattr(self, '_avatar_thumbnails', thumbnails)
        return thumbnails.get(size, None)

    def get_avatar_thumbnail_url(self, size=(80, 80)):
        tn = self.get_avatar_thumbnail(size)
        return tn.url if tn else static('images/jane-doe.png')
    
    def get_map_marker_image_url(self):
        """ Returns a static image URL to use as a map marker image, or '' if none available """
        small_avatar = self.get_avatar_thumbnail(size=(40, 40))
        return small_avatar.url if small_avatar else static('images/jane-doe.png')
    
    def media_tag_object(self):
        key = '_media_tag_cache'
        if not hasattr(self, key):
            setattr(self, key, self.media_tag)
        return getattr(self, key)
    
    def add_redirect_on_next_page(self, resolved_url):
        """ Adds a redirect-page to the user's settings redirect list.
            A middleware enforces that the user will be redirected to the first URL in the list on the next page hit. """
        redirects = self.settings.get(PROFILE_SETTING_REDIRECT_NEXT_VISIT, [])
        redirects.append(resolved_url)
        self.settings[PROFILE_SETTING_REDIRECT_NEXT_VISIT] = redirects
        self.save(update_fields=['settings'])
    
    def pop_next_redirect(self):
        """ Tries to remove the first redirect URL in the user's setting's redirect list, and return it.
            @return: A string resolved URL, or False if none existed. """
        redirects = self.settings.get(PROFILE_SETTING_REDIRECT_NEXT_VISIT, [])
        next_redirect = redirects.pop()
        if next_redirect:
            self.settings[PROFILE_SETTING_REDIRECT_NEXT_VISIT] = redirects
            self.save(update_fields=['settings'])
            return next_redirect
        return False
    

class UserProfile(BaseUserProfile):
    
    class Meta:
        app_label = 'cosinnus'
        swappable = 'COSINNUS_USER_PROFILE_MODEL'
    

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
