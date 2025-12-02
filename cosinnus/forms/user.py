# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import random
from builtins import object, str

from captcha.fields import CaptchaField
from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm
from django.contrib.auth.forms import UserCreationForm as DjUserCreationForm
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MinLengthValidator
from django.utils.translation import gettext_lazy as _
from osm_field.fields import LatitudeField, LongitudeField, OSMField

from cosinnus.conf import settings
from cosinnus.forms.dynamic_fields import _DynamicFieldsBaseFormMixin
from cosinnus.forms.managed_tags import ManagedTagFormMixin
from cosinnus.forms.mixins import PasswordValidationFormMixin
from cosinnus.forms.select2 import CommaSeparatedSelect2MultipleChoiceField
from cosinnus.models.group import CosinnusPortal, CosinnusPortalMembership
from cosinnus.models.profile import GlobalBlacklistedEmail, get_user_profile_model
from cosinnus.models.tagged import BaseTagObject, get_tag_object_model
from cosinnus.utils.user import accept_user_tos_for_portal
from cosinnus.utils.validators import validate_username

logger = logging.getLogger('cosinnus')

USER_NAME_FIELDS_MAX_LENGTH = 30


class UserKwargModelFormMixin(object):
    """
    Generic model form mixin for popping user out of the kwargs and
    attaching it to the instance.

    This mixin must precede ``forms.ModelForm`` / ``forms.Form``. The form is
    not expecting these kwargs to be passed in, so they must be popped off
    before anything else is done.
    """

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        if 'request' in kwargs:
            self.request = kwargs.pop('request')
        super(UserKwargModelFormMixin, self).__init__(*args, **kwargs)
        if self.user and hasattr(self.instance, 'user_id'):
            self.instance.user_id = self.user.id


class TermsOfServiceFormFields(forms.Form):
    """Used for the updated ToS popup and view."""

    tos_check = forms.BooleanField(label='tos_check', required=True)

    if settings.COSINNUS_SIGNUP_REQUIRES_PRIVACY_POLICY_CHECK:
        privacy_policy_check = forms.BooleanField(label='privacy_policy_check', required=True)

    if settings.COSINNUS_USERPROFILE_ENABLE_NEWSLETTER_OPT_IN:
        newsletter_opt_in = forms.BooleanField(label='newsletter_opt_in', required=False)


class UserCreationFormDynamicFieldsMixin(_DynamicFieldsBaseFormMixin):
    """Like UserProfileFormDynamicFieldsMixin, but works with the user signup form"""

    DYNAMIC_FIELD_SETTINGS = settings.COSINNUS_USERPROFILE_EXTRA_FIELDS

    # only show fields with option `in_signup` set to True
    filter_included_fields_by_option_name = 'in_signup'

    def prepare_extra_fields_initial(self):
        """no need for this, as the creation form never has any initial values"""
        pass

    def save(self, commit=True):
        """Assign the extra fields to the user's cosinnus_profile's `dynamic_fields`
        JSON field instead of model fields, after user form save"""
        ret = super().save(commit=commit)
        if commit:
            if hasattr(self, 'cleaned_data'):
                # sanity check, retrieve the user's profile (will create it if it doesnt exist)
                if not hasattr(self.instance, 'cosinnus_profile') or not self.instance.cosinnus_profile:
                    get_user_profile_model()._default_manager.get_for_user(self.instance)

                profile = self.instance.cosinnus_profile
                for field_name in self.DYNAMIC_FIELD_SETTINGS.keys():
                    profile.dynamic_fields[field_name] = self.cleaned_data.get(field_name, None)
                    profile.save()
        return ret


class UserSignupFinalizeMixin(object):
    """Mixin for `finalize_user_object_after_signup`,
    used by `UserCreationForm` and `CosinnusUserSignupSerializer`"""

    def finalize_user_object_after_signup(self, user, cleaned_data):
        """Performs extra initialization logic after a user object has just been created
        after a fresh user signup.
        This should be called before
        `UserSignupTriggerEventsMixin.trigger_events_after_user_signup`"""

        user.username = str(user.id)
        user.save()

        # create a portal membership for the new user for the current portal
        CosinnusPortalMembership.objects.get_or_create(
            group=CosinnusPortal.get_current(),
            user=user,
            defaults={
                'status': 1,
            },
        )

        media_tag = user.cosinnus_profile.media_tag
        media_tag_needs_saving = False

        # set media_tag visibility
        default_visibility = None
        # set the user's visibility to public if the setting says so
        if settings.COSINNUS_USER_DEFAULT_VISIBLE_WHEN_CREATED:
            default_visibility = BaseTagObject.VISIBILITY_ALL
        # set the user's visibility to the locked value if the setting says so
        if settings.COSINNUS_USERPROFILE_VISIBILITY_SETTINGS_LOCKED is not None:
            default_visibility = settings.COSINNUS_USERPROFILE_VISIBILITY_SETTINGS_LOCKED
        if default_visibility is not None:
            media_tag.visibility = default_visibility
            media_tag_needs_saving = True

        # set user location field if included in signup
        if settings.COSINNUS_USER_SIGNUP_INCLUDES_LOCATION_FIELD:
            if (
                cleaned_data.get('location', None)
                and cleaned_data.get('location_lat', None)
                and cleaned_data.get('location_lon', None)
            ):
                media_tag.location = cleaned_data.get('location')
                media_tag.location_lat = cleaned_data.get('location_lat')
                media_tag.location_lon = cleaned_data.get('location_lon')
                media_tag_needs_saving = True

        # set user topic field if included in signup
        if settings.COSINNUS_USER_SIGNUP_INCLUDES_TOPIC_FIELD:
            if cleaned_data.get('topics', None):
                media_tag.topics = cleaned_data.get('topics')
            media_tag_needs_saving = True

        if media_tag_needs_saving:
            media_tag.save()

        # set the user's tos_accepted flag to true and date to now
        accept_user_tos_for_portal(user, save=False)

        # set the newsletter opt-in
        if settings.COSINNUS_USERPROFILE_ENABLE_NEWSLETTER_OPT_IN:
            user.cosinnus_profile.settings['newsletter_opt_in'] = cleaned_data.get('newsletter_opt_in', False)

        user.cosinnus_profile.save()


class UserCreationForm(
    UserSignupFinalizeMixin,
    UserCreationFormDynamicFieldsMixin,
    TermsOfServiceFormFields,
    ManagedTagFormMixin,
    DjUserCreationForm,
):
    # Inherit from UserCreationForm for proper password hashing!

    class Meta(object):
        model = get_user_model()
        fields = ['username', 'email', 'password1', 'password2', 'first_name', 'tos_check']
        if settings.COSINNUS_USER_FORM_SHOW_SEPARATE_LAST_NAME:
            fields += ['last_name']
        if (
            settings.COSINNUS_MANAGED_TAGS_ENABLED
            and settings.COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_SELF
            and settings.COSINNUS_MANAGED_TAGS_IN_SIGNUP_FORM
        ):
            fields = fields + ['managed_tag_field']

    # email maxlength 220 instead of 254, to accomodate hashes to scramble them
    email = forms.EmailField(label=_('email address'), required=True, validators=[MaxLengthValidator(220)])
    first_name = forms.CharField(
        label=_('first name'),
        required=True,
        validators=[MaxLengthValidator(USER_NAME_FIELDS_MAX_LENGTH), validate_username],
    )
    last_name = forms.CharField(
        label=_('last name'), validators=[MaxLengthValidator(USER_NAME_FIELDS_MAX_LENGTH), validate_username]
    )

    if (
        settings.COSINNUS_MANAGED_TAGS_ENABLED
        and settings.COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_SELF
        and settings.COSINNUS_MANAGED_TAGS_IN_SIGNUP_FORM
    ):
        managed_tag_field = forms.CharField(required=settings.COSINNUS_MANAGED_TAGS_USERPROFILE_FORMFIELD_REQUIRED)
        managed_tag_assignment_attribute_name = 'cosinnus_profile'
    if not settings.COSINNUS_IS_INTEGRATED_PORTAL and not settings.COSINNUS_IS_SSO_PORTAL:
        captcha = CaptchaField()

    def __init__(self, *args, **kwargs):
        super(UserCreationForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = bool(settings.COSINNUS_USER_FORM_LAST_NAME_REQUIRED)

        # if the location field is to be shown in signup, show it here
        if settings.COSINNUS_USER_SIGNUP_INCLUDES_LOCATION_FIELD:
            self.fields['location'] = OSMField(
                _('Location'), blank=True, null=True, lat_field='location_lat', lon_field='location_lon'
            ).formfield()
            self.fields['location_lat'] = LatitudeField(_('Latitude'), blank=True, null=True).formfield(
                widget=forms.HiddenInput()
            )
            self.fields['location_lon'] = LongitudeField(_('Longitude'), blank=True, null=True).formfield(
                widget=forms.HiddenInput()
            )
            if settings.COSINNUS_USER_SIGNUP_LOCATION_FIELD_IS_REQUIRED:
                self.fields['location'].required = True
                self.fields['location_lat'].required = True
                self.fields['location_lon'].required = True

        # if the topic field is to be shown in signup, show it here
        if settings.COSINNUS_USER_SIGNUP_INCLUDES_TOPIC_FIELD:
            TagObject = get_tag_object_model()
            self.fields['topics'] = CommaSeparatedSelect2MultipleChoiceField(
                choices=TagObject.TOPIC_CHOICES, required=False
            )

    def is_valid(self):
        """Get the email from the form and set it as username.
        If none was set, hide the username field and let validation take its course."""
        self.data._mutable = True
        self.data['username'] = str(random.randint(100000000000, 999999999999))
        return super(UserCreationForm, self).is_valid()

    def clean_email(self):
        email = self.cleaned_data.get('email')
        username = self.cleaned_data.get('username')
        if email and UserCreationForm.Meta.model.objects.filter(email__iexact=email).exclude(username=username).count():
            raise forms.ValidationError(_('This email address already has a registered user!'))
        return email.lower()

    def save(self, commit=True):
        """Set the username equal to the userid"""
        try:
            user = None
            user = super(UserCreationForm, self).save(commit=True)
        except Exception as e:
            if user is None or not user.id:
                # bubble up exception if user wasn't saved
                raise
            else:
                # if user was saved, but a hook caused an exception, carry on
                logger.error('Non-critical error during user creation, continuing.', e)

        self.finalize_user_object_after_signup(user, self.cleaned_data)
        return user


class UserChangeForm(forms.ModelForm):
    # Inherit from UserCreationForm for proper password hashing!

    class Meta(object):
        model = get_user_model()
        fields = (
            'email',
            'first_name',
            'last_name',
        )

    first_name = forms.CharField(
        label=_('first name'),
        required=True,
        validators=[MaxLengthValidator(USER_NAME_FIELDS_MAX_LENGTH), validate_username],
    )
    last_name = forms.CharField(
        label=_('last name'), validators=[MaxLengthValidator(USER_NAME_FIELDS_MAX_LENGTH), validate_username]
    )

    def __init__(self, *args, **kwargs):
        if not settings.COSINNUS_USER_FORM_SHOW_SEPARATE_LAST_NAME:
            instance = kwargs['instance']
            if instance.last_name:
                kwargs['initial']['first_name'] = f'{instance.first_name} {instance.last_name}'
                kwargs['initial']['last_name'] = ''
        super(UserChangeForm, self).__init__(*args, **kwargs)
        self.fields['email'].required = True
        self.fields['first_name'].required = True
        if settings.COSINNUS_USER_FORM_SHOW_SEPARATE_LAST_NAME:
            self.fields['last_name'].required = bool(settings.COSINNUS_USER_FORM_LAST_NAME_REQUIRED)
        else:
            self.fields['last_name'].required = False
            self.fields['last_name'].widget = forms.HiddenInput()

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if (
            email
            and UserCreationForm.Meta.model.objects.filter(email__iexact=email)
            .exclude(username=self.instance.username)
            .count()
        ):
            raise forms.ValidationError(_('This email address already has a registered user!'))
        return email


class UserEmailLoginForm(AuthenticationForm):
    error_messages = {
        'invalid_login': _('Please enter a correct email and password. Note that both fields may be case-sensitive.'),
        'no_cookies': _(
            "Your Web browser doesn't appear to have cookies enabled. Cookies are required for logging in."
        ),
        'inactive': _('This account is inactive.'),
    }


class ValidatedPasswordChangeForm(PasswordChangeForm):
    """For some reason the Django default SetPasswordForm does not use the default password validators.
    Therefore this form includes the default password validators.
    """

    def clean_new_password2(self):
        password1 = self.cleaned_data.get('new_password1')
        password2 = self.cleaned_data.get('new_password2')
        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError(
                    self.error_messages['password_mismatch'],
                    code='password_mismatch',
                )

        validators = password_validation.get_default_password_validators()
        password_validation.validate_password(password2, self.user, password_validators=validators)
        return password2


class UserChangeEmailForm(forms.Form):
    """
    A form that lets the user change their email
    """

    error_messages = {
        'email_already_taken': _('This email address already has a registered user!'),
        'email_same': _('This email is already currently associated with your account!'),
        'email_blacklisted': _(
            'This email is blacklisted and cannot be used. You may have opted out of receiving any emails before. '
            'Please contact support to use this email address.'
        ),
    }
    email = forms.EmailField(
        label=_('New email'),
    )

    def __init__(self, user=None, *args, **kwargs):
        # support user kwarg already been set (by `PasswordValidationFormMixin` for example), or not
        self.user = getattr(self, 'user', None)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        email = email.strip().lower()
        if email == self.user.email:
            raise ValidationError(
                self.error_messages['email_same'],
                code='email_same',
            )
        if get_user_model().objects.filter(email__iexact=email).count():
            raise ValidationError(
                self.error_messages['email_already_taken'],
                code='email_already_taken',
            )
        if GlobalBlacklistedEmail.is_email_blacklisted(email):
            raise ValidationError(
                self.error_messages['email_blacklisted'],
                code='email_blacklisted',
            )
        return email


class UserChangeEmailFormWithPasswordValidation(PasswordValidationFormMixin, UserChangeEmailForm):
    """The user email change form, with added password validation logic"""

    pass


class UserGroupGuestAccessForm(forms.Form):
    """Used for having guests enter their username and ToS accept"""

    username = forms.CharField(max_length=50, required=True, validators=[MinLengthValidator(2), MaxLengthValidator(50)])
    tos_check = forms.BooleanField(label='tos_check', required=True)

    if settings.COSINNUS_SIGNUP_REQUIRES_PRIVACY_POLICY_CHECK:
        privacy_policy_check = forms.BooleanField(label='privacy_policy_check', required=True)
