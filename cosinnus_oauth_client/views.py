import requests
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.views import PasswordSetView
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.providers.oauth2.views import OAuth2Adapter, OAuth2CallbackView, OAuth2LoginView
from allauth.socialaccount.views import ConnectionsView
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic.base import TemplateView

from cosinnus.utils.urls import redirect_with_next

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
        headers = {'Authorization': 'Bearer {0}'.format(token.meeting_id)}
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        extra_data = resp.json()
        socialaccount = self.get_provider().sociallogin_from_response(request, extra_data)
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
            return '{}?provider={}'.format(reverse_lazy('socialaccount_connections'), provider)
        return reverse_lazy('socialaccount_connections')


class CustomConnectionView(SocialAppMixin, ConnectionsView):
    def dispatch(self, request, *args, **kwargs):
        if request.method == 'GET' and not request.GET.get('provider', False):
            provider = self.get_single_social_apps_provider()
            if provider:
                return redirect('{}?provider={}'.format(reverse_lazy('socialaccount_connections'), provider))
            else:
                raise Http404
        return super().dispatch(request, *args, **kwargs)


custom_connections = login_required(CustomConnectionView.as_view())


class CustomSetPasswordView(SocialAppMixin, PasswordSetView):
    pass


custom_password_set = login_required(CustomSetPasswordView.as_view())


class OauthLoginWelcomeView(TemplateView):
    template_name = 'cosinnus_oauth_client/welcome_oauth.html'


welcome_oauth = login_required(OauthLoginWelcomeView.as_view())
