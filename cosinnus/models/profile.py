# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
import six
import django

from django.apps import apps
from django.core.exceptions import ObjectDoesNotExist, ImproperlyConfigured
from django.urls import reverse
from django.core.cache import cache
from django.db import models, transaction
from django.db.models.signals import post_save, class_prepared
from django.utils.encoding import python_2_unicode_compatible, force_text
from django.utils.text import slugify
from django.utils.translation import ugettext_lazy as _, pgettext_lazy

from jsonfield import JSONField

from cosinnus.conf import settings
from cosinnus.conf import settings as cosinnus_settings
from cosinnus.utils.files import get_avatar_filename, image_thumbnail,\
    image_thumbnail_url
from cosinnus.models.group import CosinnusPortal, CosinnusPortalMembership
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
from annoying.functions import get_object_or_None
from cosinnus.models.mixins.indexes import IndexingUtilsMixin

import logging
from django import forms
from django_countries.fields import CountryField
from django.contrib.contenttypes.fields import GenericRelation
from cosinnus.models.managed_tags import CosinnusManagedTag,\
    CosinnusManagedTagAssignmentModelMixin

logger = logging.getLogger('cosinnus')

# if a user profile has this settings, its user has not yet confirmed a new email
# address and this long is bound to his old email (or to a scrambled, unusable one if they just registered)
PROFILE_SETTING_EMAIL_TO_VERIFY = 'email_to_verify'
PROFILE_SETTING_EMAIL_VERFICIATION_TOKEN = 'email_verification_pwd'
# a list of urls to redirect the user to on next page hit (only first in list), enforced by middleware
PROFILE_SETTING_REDIRECT_NEXT_VISIT = 'redirect_next'
# first login datetime, used to determine if user first logged in
PROFILE_SETTING_FIRST_LOGIN = 'first_login'
PROFILE_SETTING_ROCKET_CHAT_ID = 'rocket_chat_id'
PROFILE_SETTING_ROCKET_CHAT_USERNAME = 'rocket_chat_username'
PROFILE_SETTING_WORKSHOP_PARTICIPANT = 'is_workshop_participant'
PROFILE_SETTING_WORKSHOP_PARTICIPANT_NAME = 'workshop_participant_name'
PROFILE_SETTING_COSINUS_OAUTH_LOGIN = 'has_logged_in_with_cosinnus_oauth'


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
class BaseUserProfile(IndexingUtilsMixin, FacebookIntegrationUserProfileMixin,
                      CosinnusManagedTagAssignmentModelMixin, models.Model):
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
        related_name='cosinnus_profile', on_delete=models.CASCADE)
    
    avatar = models.ImageField(_("Avatar"), null=True, blank=True,
        upload_to=get_avatar_filename)
    description = models.TextField(verbose_name=_('Description'), blank=True, null=True)
    media_tag = models.OneToOneField(settings.COSINNUS_TAG_OBJECT_MODEL,
        blank=True, null=True, editable=False, on_delete=models.SET_NULL)
    website = models.URLField(_('Website'), max_length=100, blank=True, null=True)
    language = models.CharField(_('Language'), max_length=2,
        choices=settings.LANGUAGES, default='de')
    # display and inclusion in forms is dependent on setting `COSINNUS_USER_SHOW_MAY_BE_CONTACTED_FIELD`
    may_be_contacted = models.BooleanField(_('May be contacted'), default=False)
    
    # UI and other preferences and extra settings for the user account
    settings = JSONField(default={})
    extra_fields = JSONField(default={}, blank=True,
                help_text='Extra userprofile fields for each portal, as defined in `settings.COSINNUS_USERPROFILE_EXTRA_FIELDS`')
    
    managed_tag_assignments = GenericRelation('cosinnus.CosinnusManagedTagAssignment')
    
    objects = BaseUserProfileManager()

    SKIP_FIELDS = ['id', 'user', 'user_id', 'media_tag', 'media_tag_id', 'settings', 'managed_tag_assignments']\
                    + getattr(cosinnus_settings, 'COSINNUS_USER_PROFILE_ADDITIONAL_FORM_SKIP_FIELDS', [])
    
    # this indicates that objects of this model are in some way always visible by registered users
    # on the platform, no matter their visibility settings, and thus subject to moderation 
    cosinnus_always_visible_by_users_moderator_flag = True
    
    _settings = None
    
    
    class Meta(object):
        abstract = True
        
    def __init__(self, *args, **kwargs):
        super(BaseUserProfile, self).__init__(*args, **kwargs)
        self._settings = copy.deepcopy(self.settings)
        
    def __str__(self):
        return six.text_type(self.user)
    
    def get_icon(self):
        """ Returns the font-awesome icon specific to this object type """
        return 'fa-user'
    
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
            existing = self._meta.model._default_manager.get(user=self.user)
            # workaround for http://goo.gl/4I8Ok
            self.id = existing.id  # force update instead of insert
        except ObjectDoesNotExist:
            pass
        super(BaseUserProfile, self).save(*args, **kwargs)
        
        if created:
            # send creation signal
            signals.userprofile_created.send(sender=self, profile=self)
        
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
        self._settings = copy.deepcopy(self.settings)

    def get_absolute_url(self):
        return group_aware_reverse('cosinnus:profile-detail', kwargs={'username': self.user.username})

    @classmethod
    def get_optional_fieldnames(cls):
        """
        Iterates over all fields defined in the user profile and returns a list
        of field names.

        The list will only contain those fields not listed in ``SKIP_FIELDS``.
        """
        return list(set([f.name for f in cls._meta.get_fields()]) - set(cls.SKIP_FIELDS))

    def get_optional_fields(self):
        """
        Iterates over all fields defined in the user profile and returns a list
        of dicts with the keys ``name`` and ``value``.

        The list will only contain those fields not listed in ``SKIP_FIELDS``.
        """
        all_fields = [f.name for f in self._meta.get_fields()]
        optional_fields = []
        for name in all_fields:
            if name in self.SKIP_FIELDS:
                continue
            value = getattr(self, name, None)
            if value:
                field = self._meta.get_field(name)
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
    def cosinnus_projects(self):
        """ Returns all projects this user is a member or admin of """
        from cosinnus.models.group_extra import CosinnusProject
        return CosinnusProject.objects.get_for_user(self.user)
    
    @property
    def cosinnus_societies(self):
        """ Returns all societies this user is a member or admin of """
        from cosinnus.models.group_extra import CosinnusSociety
        return CosinnusSociety.objects.get_for_user(self.user)
    
    @property
    def avatar_url(self):
        return self.avatar.url if self.avatar else None
    
    def get_avatar_thumbnail(self, size=(80, 80)):
        return image_thumbnail(self.avatar, size)

    def get_avatar_thumbnail_url(self, size=(80, 80)):
        return image_thumbnail_url(self.avatar, size) or static('images/jane-doe-small.png')
    
    def get_image_field_for_icon(self):
        return self.avatar or static('images/jane-doe.png')
    
    def media_tag_object(self):
        key = '_media_tag_cache'
        if not hasattr(self, key):
            setattr(self, key, self.media_tag)
        return getattr(self, key)
    
    def add_redirect_on_next_page(self, resolved_url, message=None, priority=False):
        """ Adds a redirect-page to the user's settings redirect list.
            A middleware enforces that the user will be redirected to the first URL in the list on the next page hit.
            @param message: (optional) Can be a string, that will be displayed as success-message at redirect time.
                             i18n u_gettext will be applied *later, at redirect time* to this string! 
            @param priority: if set to `True`, will insert the redirect as first URL, so it will be the next one in queue """
        redirects = self.settings.get(PROFILE_SETTING_REDIRECT_NEXT_VISIT, [])
        if priority:
            redirects.insert(0, (resolved_url, message))
        else:
            redirects.append((resolved_url, message))
        self.settings[PROFILE_SETTING_REDIRECT_NEXT_VISIT] = redirects
        self.save(update_fields=['settings'])
    
    def pop_next_redirect(self):
        """ Tries to remove the first redirect URL in the user's setting's redirect list, and return it.
            @return: A tuple (string resolved URL, message), or False if none existed. """
        redirects = self.settings.get(PROFILE_SETTING_REDIRECT_NEXT_VISIT, [])
        if not redirects:
            return False
        next_redirect = redirects.pop(0)
        if next_redirect:
            self.settings[PROFILE_SETTING_REDIRECT_NEXT_VISIT] = redirects
            self.save(update_fields=['settings'])
            return next_redirect
        return False

    def get_new_rocket_username(self):
        """ Builds rocket username based upon first and last name (or ID if not given) """
        user = self.user
        if user.first_name or user.last_name:
            username = '.'.join(filter(None, [slugify(user.first_name), slugify(user.last_name)]))
        else:
            username = str(user.id)

        def is_username_free(username):
            value = f'"{PROFILE_SETTING_ROCKET_CHAT_USERNAME}":"{username}"'
            queryset = get_user_profile_model().objects.filter(settings__contains=value)
            return queryset.count() == 0

        i = 1
        while True:
            if i == 1 and is_username_free(username):
                break
            else:
                new_username = f'{username}{i}'
                if is_username_free(new_username):
                    username = new_username
                    break
            i += 1
            if i > 1000:
                raise Exception('Name is very popular')
        return username

    @property
    def rocket_username(self):
        """ Retrieves or creates rocket username """
        username = self.settings.get(PROFILE_SETTING_ROCKET_CHAT_USERNAME, '')
        if not username:
            username = self.get_new_rocket_username()
            self.settings[PROFILE_SETTING_ROCKET_CHAT_USERNAME] = username
            get_user_profile_model().objects.filter(id=self.id).update(settings=self.settings)
        return username

    @rocket_username.setter
    def rocket_username(self, username):
        """ Sets new username for Rocket.Chat """
        self.settings[PROFILE_SETTING_ROCKET_CHAT_USERNAME] = username

    @property
    def workshop_user_name(self):
        return self.settings.get(PROFILE_SETTING_WORKSHOP_PARTICIPANT_NAME)

    @property
    def readable_workshop_user_name(self):
        settings_name = self.settings.get(PROFILE_SETTING_WORKSHOP_PARTICIPANT_NAME)
        return settings_name.split('__')[-1]

    @property
    def is_workshop_participant(self):
        return self.settings.get(PROFILE_SETTING_WORKSHOP_PARTICIPANT, False)


class UserProfile(BaseUserProfile):
    
    class Meta(object):
        app_label = 'cosinnus'
        swappable = 'COSINNUS_USER_PROFILE_MODEL'
    

def get_user_profile_model():
    "Return the cosinnus user profile model that is active in this project"
    from django.core.exceptions import ImproperlyConfigured
    from cosinnus.conf import settings

    try:
        app_label, model_name = settings.COSINNUS_USER_PROFILE_MODEL.split('.')
    except ValueError:
        raise ImproperlyConfigured("COSINNUS_USER_PROFILE_MODEL must be of the form 'app_label.model_name'")
    user_profile_model = apps.get_model(app_label, model_name)
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



class GlobalUserNotificationSettingManager(models.Manager):
    """ Cached acces to user notification settings  """
    
    _NOTIFICATION_CACHE_KEY = 'cosinnus/core/portal/%d/user/%d/slugs' # portal_id, user_id  --> setting value (int)
    
    def get_for_user(self, user):
        """ Returns the cached setting value for this user's global notification setting. """
        setting = cache.get(self._NOTIFICATION_CACHE_KEY % (CosinnusPortal.get_current().id, user.id))
        if setting is None:
            setting = self.get_object_for_user(user).setting
            cache.set(self._NOTIFICATION_CACHE_KEY % (CosinnusPortal.get_current().id, user.id), setting,
                settings.COSINNUS_GLOBAL_USER_NOTIFICATION_SETTING_CACHE_TIMEOUT)
        return setting
    
    def get_object_for_user(self, user):
        """ Returns the settings object for this user, creates one if it didn't exist yet.
            Will return uncached, as this should be asked for seldomly and will need to be fresh anyways """
        try:
            obj = self.get(user=user, portal=CosinnusPortal.get_current())
        except self.model.DoesNotExist:
            obj = self.create(user=user, portal=CosinnusPortal.get_current())
        return obj
    
    def clear_cache_for_user(self, user):
        cache.delete(self._NOTIFICATION_CACHE_KEY % (CosinnusPortal.get_current().id, user.id))
    

class GlobalUserNotificationSetting(models.Model):
    """
    A global setting for whether users want to receive mail *at all*, or in which intervals.
    """
    # do not send emails ever
    SETTING_NEVER = 0
    # send all emails and notifications immediately
    SETTING_NOW = 1
    # aggregates notifications for a daily email, sends other mail immediately
    SETTING_DAILY = 2
    # aggregates notifications for a weekly email, sends other mail immediately
    SETTING_WEEKLY = 3
    # notifications are sent out based on settings for each project/group, sends other mail immediately
    SETTING_GROUP_INDIVIDUAL = 4
    
    SETTING_CHOICES = (
        (SETTING_NEVER, pgettext_lazy('answer to "i wish to receive notification emails:"', 'Never (we will not send you any emails)')),
        (SETTING_NOW, pgettext_lazy('answer to "i wish to receive notification emails:"', 'Immediately (an individual email per event)')),
        (SETTING_DAILY, pgettext_lazy('answer to "i wish to receive notification emails:"', 'In a Daily Report')),
        (SETTING_WEEKLY, pgettext_lazy('answer to "i wish to receive notification emails:"', 'In a Weekly Report')),
        (SETTING_GROUP_INDIVIDUAL, pgettext_lazy('answer to "i wish to receive notification emails:"', 'Individual settings for each Project/Group...')),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, editable=False, related_name='cosinnus_notification_settings', on_delete=models.CASCADE)
    portal = models.ForeignKey('cosinnus.CosinnusPortal', verbose_name=_('Portal'), related_name='user_notification_settings', 
        null=False, blank=False, default=1, on_delete=models.CASCADE)
    setting = models.PositiveSmallIntegerField(choices=SETTING_CHOICES,
            default=settings.COSINNUS_DEFAULT_GLOBAL_NOTIFICATION_SETTING,
            help_text='Determines if the user wants no mail, immediate mails,s aggregated mails, or group specific settings')
    last_modified = models.DateTimeField(_('Last modified'), auto_now=True, editable=False)
    
    objects = GlobalUserNotificationSettingManager()
    
    class Meta(object):
        unique_together = ('user', 'portal', )
    
    def save(self, *args, **kwargs):
        super(GlobalUserNotificationSetting, self).save(*args, **kwargs)
        self._meta.model.objects.clear_cache_for_user(self.user)
    

class GlobalBlacklistedEmail(models.Model):
    """
    A list of blacklisted emails that will never ever receive emails from us, to comply with list-unsubscribe.
    Only exception are email-validation mails.
    """
    
    email = models.EmailField(_('email address'), unique=True, db_index=True)
    created = models.DateTimeField(verbose_name=_('Created'), editable=False, auto_now_add=True)
    portal = models.ForeignKey('cosinnus.CosinnusPortal', verbose_name=_('Portal'), related_name='blacklisted_emails', 
        null=False, blank=False, default=1, on_delete=models.CASCADE)
    
    @classmethod
    def add_for_email(cls, email):
        """ Will add an email to the blacklist if it doesn't exist yet if no user is registered with that email 
            or doesn't have a portal membership in this current portal.
            Otherwise will simply set the global "no-email" setting for that user. """
        from django.contrib.auth import get_user_model
        user = get_object_or_None(get_user_model(), email=email, is_active=True)
        portal_membership = get_object_or_None(CosinnusPortalMembership, user=user, group=CosinnusPortal.get_current())
        if portal_membership:
            with transaction.atomic():
                setting_object = GlobalUserNotificationSetting.objects.get_object_for_user(user) 
                setting_object.setting = GlobalUserNotificationSetting.SETTING_NEVER
                setting_object.save()
                logger.warn('GlobalBlacklistedEmail: Set a global user notification to NEVER from blacklist', 
                            extra={'email': user.email, 'portal': CosinnusPortal.get_current().id})
                cls.remove_for_email(email)
        else:
            cls.objects.get_or_create(email=email, portal=CosinnusPortal.get_current())
        
    @classmethod
    def is_email_blacklisted(cls, email):
        return (get_object_or_None(cls, email=email, portal=CosinnusPortal.get_current()) is not None)
    
    @classmethod
    def remove_for_email(cls, email):
        """ Will remove an email if it exists """
        entry = get_object_or_None(cls, email=email, portal=CosinnusPortal.get_current())
        if entry:
            entry.delete()


def _make_country_formfield(**kwargs):
    return CountryField(
        blank=True,
        blank_label=_('--- No country selected ---')
    ).formfield(**kwargs)


class _UserProfileFormExtraFieldsBaseMixin(object):
    """ Base for the Mixins for the UserProfile or User modelforms that
        add functionality for by-portal configured extra profile form fields """
    
    # a choice of field types for the settings dict values of `COSINNUS_USERPROFILE_EXTRA_FIELDS`
    # these will be initialized as variable form fields for the fields in `self.extra_fields`
    EXTRA_FIELD_TYPES = {
        'text': forms.CharField,
        'boolean': forms.BooleanField,
        'country': _make_country_formfield,
    }
    # if set to a string, will only include such fields in the form
    # that have the given option name set to True in `COSINNUS_USERPROFILE_EXTRA_FIELDS`
    filter_included_fields_by_option_name = None
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prepare_extra_fields_initial()
        self.prepare_extra_fields()
        if 'extra_fields' in self.fields:
            del self.fields['extra_fields']
            
    def prepare_extra_fields_initial(self):
        """ Stub for settting the initial data for `self.extra_fields` as defined in
            `settings.COSINNUS_USERPROFILE_EXTRA_FIELDS`.
            Only a form with an UpdateView needs to implement this.  """
        pass
    
    def prepare_extra_fields(self):
        """ Creates extra fields for `self.extra_fields` as defined in
            `settings.COSINNUS_USERPROFILE_EXTRA_FIELDS` """
        field_map = {}
        for field_name, options in settings.COSINNUS_USERPROFILE_EXTRA_FIELDS.items():
            if field_name in self.fields:
                raise ImproperlyConfigured(f'COSINNUS_USERPROFILE_EXTRA_FIELDS: {field_name} clashes with an existing UserProfile field!')
            if not 'type' in options:
                raise ImproperlyConfigured(f'COSINNUS_USERPROFILE_EXTRA_FIELDS: {field_name} does not define a "type" attribute of {self.__class__.__name__}.EXTRA_FIELD_TYPES!')
            if not options['type'] in self.EXTRA_FIELD_TYPES:
                raise ImproperlyConfigured(f'COSINNUS_USERPROFILE_EXTRA_FIELDS: {field_name}\'s "type" attribute was not found in {self.__class__.__name__}.EXTRA_FIELD_TYPES!')
            # filter by whether a given option is set
            if self.filter_included_fields_by_option_name \
                    and not options.get(self.filter_included_fields_by_option_name, False):
                continue
            
            formfield_class = self.EXTRA_FIELD_TYPES[options['type']]
            self.fields[field_name] = formfield_class(
                label=options.get('label', None),
                initial=self.initial.get(field_name, None),
                required=options.get('required', False),
            )
            setattr(self.fields[field_name], 'label', options.get('label', None))
            setattr(self.fields[field_name], 'legend', options.get('legend', None))
            setattr(self.fields[field_name], 'placeholder', options.get('placeholder', None))
            
            # "register" the extra field additionally
            field_map[field_name] = self.fields[field_name]
            
        setattr(self, 'extra_field_list', field_map.keys())
        setattr(self, 'extra_field_items', field_map.items())
    
    
class UserProfileFormExtraFieldsMixin(_UserProfileFormExtraFieldsBaseMixin):
    """ Mixin for the UserProfile modelform that
        adds functionality for by-portal configured extra profile form fields """
    
    def prepare_extra_fields_initial(self):
        """ Set the initial data for `self.extra_fields` as defined in
            `settings.COSINNUS_USERPROFILE_EXTRA_FIELDS` """
        for field_name in settings.COSINNUS_USERPROFILE_EXTRA_FIELDS.keys():
            if field_name in self.instance.extra_fields:
                self.initial[field_name] = self.instance.extra_fields[field_name]
        
    def full_clean(self):
        """ Assign the extra fields to the `extra_fields` the userprofile JSON field
            instead of model fields, during regular form saving """
        super().full_clean()
        if hasattr(self, 'cleaned_data'):
            for field_name in settings.COSINNUS_USERPROFILE_EXTRA_FIELDS.keys():
                self.instance.extra_fields[field_name] = self.cleaned_data.get(field_name, None)


class UserCreationFormExtraFieldsMixin(_UserProfileFormExtraFieldsBaseMixin):
    """ Like UserProfileFormExtraFieldsMixin, but works with the user signup form """
    
    # only show fields with option `in_signup` set to True
    filter_included_fields_by_option_name = 'in_signup'
    
    def save(self, commit=True):
        """ Assign the extra fields to the user's cosinnus_profile's `extra_fields` 
        JSON field instead of model fields, after user form save """
        ret = super().save(commit=commit)
        if commit:
            if hasattr(self, 'cleaned_data'):
                # sanity check, retrieve the user's profile (will create it if it doesnt exist)
                if not self.instance.cosinnus_profile:
                    get_user_profile_model()._default_manager.get_for_user(self.instance)
                
                profile = self.instance.cosinnus_profile
                for field_name in settings.COSINNUS_USERPROFILE_EXTRA_FIELDS.keys():
                    profile.extra_fields[field_name] = self.cleaned_data.get(field_name, None)
                    profile.save()
        return ret
    