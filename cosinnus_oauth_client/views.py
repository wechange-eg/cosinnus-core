from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2CallbackView,
                                                          OAuth2LoginView)
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.views import ConnectionsView
from allauth.account.views import PasswordSetView

from allauth.socialaccount.models import SocialApp

from cosinnus.core.mail import send_html_mail_threaded, get_common_mail_context
from cosinnus.utils.urls import redirect_with_next

from django.urls import reverse
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib import messages
from cosinnus.templatetags.cosinnus_tags import textfield
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.http import Http404

import requests

from .provider import CosinnusOauthClientProvider


class CosinusAccountAdapter(DefaultAccountAdapter):

    def get_login_redirect_url(self, request):
        return redirect_with_next(reverse('cosinnus:user-dashboard'), self.request)

    def is_open_for_signup(self, request):
        return False


class CosinusSocialAccountAdapter(DefaultSocialAccountAdapter):

    def is_open_for_signup(self, request, sociallogin):
        return True


class CosinnusOauthClientAdapter(OAuth2Adapter):
    provider_id = CosinnusOauthClientProvider.id
    access_token_url = '{}/o/token/'.format(settings.COSINNUS_OAUTH_SERVER_BASEURL)
    user_url = '{}/o/user/'.format(settings.COSINNUS_OAUTH_SERVER_BASEURL)
    authorize_url = '{}/o/authorize/'.format(settings.COSINNUS_OAUTH_SERVER_BASEURL)

    def complete_login(self, request, app, token, **kwargs):
        url = self.user_url
        headers = {'Authorization': 'Bearer {0}'.format(token.token)}
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        extra_data = resp.json()
        socialaccount = self.get_provider().sociallogin_from_response(request,
                                                                      extra_data)

        if request.session.get('socialaccount_state'):
            state = request.session.get('socialaccount_state')
            process = state[0].get('process')
            if process == 'connect':
                messages.add_message(request,
                             messages.SUCCESS,
                             _('Successfully connected account'))
        return socialaccount


oauth2_login = OAuth2LoginView.adapter_view(CosinnusOauthClientAdapter)
oauth2_callback = OAuth2CallbackView.adapter_view(CosinnusOauthClientAdapter)


class SocialAppMixin:

    def get_single_social_apps_provider(self):
        social_apps = SocialApp.objects.all()
        if social_apps.count() == 1:
            return social_apps.first().provider

    def get_success_url(self):
        provider = self.request.POST.get('provider', False)
        if not provider:
            provider = self.get_single_social_apps_provider()

        if provider:
            return '{}?provider={}'.format(reverse_lazy("socialaccount_connections"), provider)
        return reverse_lazy("socialaccount_connections")

class CustomConnectionView(SocialAppMixin, ConnectionsView):

    def dispatch(self, request, *args, **kwargs):
        if request.method == "GET" and not request.GET.get('provider', False):
            provider = self.get_single_social_apps_provider()
            if provider:
                return redirect('{}?provider={}'.format(reverse_lazy("socialaccount_connections"), provider))
            else:
                raise Http404
        return super().dispatch(request, *args, **kwargs)

    def send_disconnect_mail(self, user, provider, request):
        data = get_common_mail_context(request)
        data.update({
            'user': user,
            'provider': provider
        })
        subj_user = render_to_string('cosinnus/mail/notification_after_oauth_account_disconnect.txt', data)
        text = textfield(render_to_string('cosinnus/mail/notification_after_oauth_account_disconnect.html', data))
        send_html_mail_threaded(user, subj_user, text)

    def form_valid(self, form):
        messages.add_message(self.request,
                             messages.SUCCESS,
                             _('Successfully removed connection.'))
        user = self.request.user
        provider = form.cleaned_data.get('account').provider
        self.send_disconnect_mail(user, provider, self.request)
        return super().form_valid(form)

custom_connections = login_required(CustomConnectionView.as_view())

class CustomSetPasswordView(SocialAppMixin, PasswordSetView):
    pass

custom_password_set = login_required(CustomSetPasswordView.as_view())
