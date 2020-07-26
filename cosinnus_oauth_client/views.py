from allauth.socialaccount.providers.oauth2.views import (OAuth2Adapter,
                                                          OAuth2CallbackView,
                                                          OAuth2LoginView)
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from cosinnus.utils.urls import redirect_with_next
from django.urls import reverse

from django.conf import settings
from cosinnus.models.profile import get_user_profile_model

import requests

from .provider import CosinnusOauthClientProvider


class CosinusAllauthRedirectAdapter(DefaultAccountAdapter):

    def get_login_redirect_url(self, request):
        return redirect_with_next(reverse('cosinnus:user-dashboard'), self.request)


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
        return socialaccount


oauth2_login = OAuth2LoginView.adapter_view(CosinnusOauthClientAdapter)
oauth2_callback = OAuth2CallbackView.adapter_view(CosinnusOauthClientAdapter)

class CustomConnectionView(ConnectionsView):

    def get_success_url(self):
        provider = self.request.POST.get('provider', False)
        if provider:
            return '{}/?provider={}'.format(reverse_lazy("socialaccount_connections"), provider)
        return reverse_lazy("socialaccount_connections")

custom_connections = login_required(CustomConnectionView.as_view())

class CustomSetPasswordView(PasswordSetView):

    def get_success_url(self):
        return reverse_lazy('password_change')

custom_password_set = login_required(CustomSetPasswordView.as_view())
