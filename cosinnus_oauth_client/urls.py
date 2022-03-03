from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns

from .provider import CosinnusOauthClientProvider

urlpatterns = default_urlpatterns(CosinnusOauthClientProvider)
