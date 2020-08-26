import requests
import tempfile

from django.core import files

from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from cosinnus.models.profile import get_user_profile_model
from cosinnus.models.group import CosinnusPortalMembership, CosinnusPortal
from cosinnus.conf import settings
from cosinnus.utils.urls import redirect_with_next
from cosinnus.models.tagged import BaseTagObject
from cosinnus.utils.user import accept_user_tos_for_portal
from django.urls import reverse
from django.contrib import messages
from django import forms
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _, get_language

from cosinnus.core.mail import send_html_mail_threaded, get_common_mail_context
from cosinnus.templatetags.cosinnus_tags import textfield

from cosinnus.forms.user import TermsOfServiceFormFields
from cosinnus.models.profile import PROFILE_SETTING_COSINUS_OAUTH_LOGIN


class SocialSignupProfileSettingsForm(SocialSignupForm, TermsOfServiceFormFields):
    email = forms.EmailField(widget=forms.HiddenInput())
    username = forms.CharField(widget=forms.HiddenInput())
    first_name = forms.CharField(widget=forms.HiddenInput())
    last_name = forms.CharField(widget=forms.HiddenInput(), required=False)
    copy_profile = forms.BooleanField(required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.sociallogin.account.provider == 'wechange':
            del self.fields['copy_profile']

    def custom_signup(self, request, user):
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

        self.send_welcome_mail(user, request)
        messages.add_message(request,
                             messages.SUCCESS,
                             _('Successfully signed in as {}.').format(user.get_full_name()))

    def setup_profile(self, user):
        if not user.cosinnus_profile:
            return get_user_profile_model()._default_manager.get_for_user(user)
        return user.cosinnus_profile

    def set_base_profile_data(self, profile, request):
        # set language
        lang = get_language()
        profile.language = lang
        profile.save(update_fields=['language'])

        copy_profile = self.cleaned_data.get('copy_profile')
        welcome_page = '{}?copy_profile={}'.format(reverse('welcome_oauth'),
                                                   copy_profile)
        profile.add_redirect_on_next_page(redirect_with_next(welcome_page, request),
            message=None, priority=True)

        # add welcomepage
        if getattr(settings, 'COSINNUS_SHOW_WELCOME_SETTINGS_PAGE', True):
            profile.add_redirect_on_next_page(
                redirect_with_next(reverse('cosinnus:welcome-settings'),
                    request),
                message=None, priority=True)

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
            })

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
        token = self.sociallogin.token
        profile_url = '{}/o/profile/'.format(settings.COSINNUS_OAUTH_SERVER_BASEURL)
        headers = {'Authorization': 'Bearer {0}'.format(token.token)}
        resp = requests.get(profile_url, headers=headers)
        resp.raise_for_status()
        return resp.json()

    def send_welcome_mail(self, user, request):
        data = get_common_mail_context(request)
        provider = self.sociallogin.account.provider
        data.update({
            'user': user,
            'provider': provider
        })
        subj_user = render_to_string('cosinnus_oauth_client/mail/welcome_after_oauth_signup_subj.txt', data)
        text = textfield(render_to_string('cosinnus_oauth_client/mail/welcome_after_oauth_signup.html', data))
        send_html_mail_threaded(user, subj_user, text)
