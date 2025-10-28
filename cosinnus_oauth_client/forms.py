import tempfile

import requests
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django import forms
from django.contrib import messages
from django.core import files
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _

from cosinnus.conf import settings
from cosinnus.core.mail import get_common_mail_context, send_html_mail_threaded
from cosinnus.forms.user import TermsOfServiceFormFields
from cosinnus.models.group import CosinnusPortal, CosinnusPortalMembership
from cosinnus.models.profile import PROFILE_SETTING_COSINUS_OAUTH_LOGIN, get_user_profile_model
from cosinnus.models.tagged import BaseTagObject
from cosinnus.templatetags.cosinnus_tags import textfield
from cosinnus.utils.urls import redirect_with_next
from cosinnus.utils.user import accept_user_tos_for_portal


class SocialSignupProfileSettingsForm(SocialSignupForm, TermsOfServiceFormFields):
    email = forms.EmailField(widget=forms.HiddenInput())
    username = forms.CharField(widget=forms.HiddenInput())
    first_name = forms.CharField(widget=forms.HiddenInput())
    last_name = forms.CharField(widget=forms.HiddenInput(), required=False)
    copy_profile = forms.BooleanField(required=False)

    error_messages = {
        'email_taken': _(
            'An account already exists with this e-mail address.'
            ' To make sure that you are the owner of this account'
            ' please sign in to that account first, then connect'
            ' your {} account.'
        )
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.sociallogin.account.provider == 'wechange':
            del self.fields['copy_profile']

    def custom_signup(self, request, user):
        user = self.set_username(user)
        profile = self.setup_profile(user)
        accept_user_tos_for_portal(user)
        base_profile = self.set_base_profile_data(profile, request)

        self.add_portal_membership(user)

        if self.cleaned_data.get('copy_profile'):
            profile_data = self.fetch_profile_data()
            for key, value in profile_data.items():
                if key == 'avatar' and value:
                    self.download_and_save_avatar(value, user.cosinnus_profile)
                elif key == 'media_tag' and value:
                    self.update_media_tag(value, base_profile)
                else:
                    setattr(base_profile, key, value)
            base_profile.save()

        if settings.COSINNUS_SSO_SEND_WELCOME_MAIL:
            self.send_welcome_mail(user, request)
        messages.add_message(request, messages.SUCCESS, _('Successfully signed in as {}.').format(user.get_full_name()))

    def validate_unique_email(self, value):
        try:
            return super().validate_unique_email(value)
        except forms.ValidationError:
            provider = self.sociallogin.account.get_provider()
            raise forms.ValidationError(self.error_messages['email_taken'].format(provider.name))

    def set_username(self, user):
        """Set username to id instead of username from provider"""
        user.username = str(user.id)
        user.save()
        return user

    def setup_profile(self, user):
        if not user.cosinnus_profile:
            return get_user_profile_model()._default_manager.get_for_user(user)
        return user.cosinnus_profile

    def set_base_profile_data(self, profile, request):
        # set email verified, as we trust the emails from the sso provider
        profile.email_verified = True

        # set language
        lang = get_language()
        profile.language = lang
        profile.save(update_fields=['language'])

        copy_profile = self.cleaned_data.get('copy_profile')
        welcome_page = '{}?copy_profile={}'.format(reverse('welcome_oauth'), copy_profile)
        profile.add_redirect_on_next_page(redirect_with_next(welcome_page, request), message=None, priority=True)

        # set visibility
        if settings.COSINNUS_USER_DEFAULT_VISIBLE_WHEN_CREATED:
            media_tag = profile.media_tag
            media_tag.visibility = BaseTagObject.VISIBILITY_ALL
            media_tag.save()

        # set the newsletter opt-in
        if settings.COSINNUS_USERPROFILE_ENABLE_NEWSLETTER_OPT_IN:
            profile.settings['newsletter_opt_in'] = self.cleaned_data.get('newsletter_opt_in')

        profile.settings[PROFILE_SETTING_COSINUS_OAUTH_LOGIN] = True

        profile.save()
        return profile

    def add_portal_membership(self, user):
        CosinnusPortalMembership.objects.get_or_create(
            group=CosinnusPortal.get_current(),
            user=user,
            defaults={
                'status': 1,
            },
        )

    def update_media_tag(self, media_tag_dict, profile):
        media_tag = profile.media_tag
        for key, value in media_tag_dict.items():
            setattr(media_tag, key, value)
        media_tag.save()

    def download_and_save_avatar(self, url, profile):
        image_url = '{}{}'.format(settings.COSINNUS_OAUTH_SERVER_BASEURL, url)
        request = requests.get(image_url, stream=True)

        if request.status_code != requests.codes.ok:
            return None

        file_name = image_url.split('/')[-1]
        lf = tempfile.NamedTemporaryFile()
        for block in request.iter_content(1024 * 8):
            if not block:
                break
            lf.write(block)

        profile.avatar.save(file_name, files.File(lf))
        return profile

    def fetch_profile_data(self):
        token = self.sociallogin.meeting_id
        profile_url = '{}/o/profile/'.format(settings.COSINNUS_OAUTH_SERVER_BASEURL)
        headers = {'Authorization': 'Bearer {0}'.format(token.meeting_id)}
        resp = requests.get(profile_url, headers=headers)
        resp.raise_for_status()
        return resp.json()

    def send_welcome_mail(self, user, request):
        data = get_common_mail_context(request)
        provider = self.sociallogin.account.get_provider().name
        data.update({'user': user, 'provider': provider})
        subj_user = render_to_string('cosinnus_oauth_client/mail/welcome_after_oauth_signup_subj.txt', data)
        text = textfield(render_to_string('cosinnus_oauth_client/mail/welcome_after_oauth_signup.html', data))
        send_html_mail_threaded(user, subj_user, text)
