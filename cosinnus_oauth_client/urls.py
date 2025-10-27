from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from allauth.socialaccount.views import signup
from django.urls import include, path

from cosinnus_oauth_client.provider import CosinnusOauthClientProvider
from cosinnus_oauth_client.views import custom_connections, custom_password_set, welcome_oauth

# TODO: consider usind cosinnus_app and urlregistry

# oauth2 login and callback urls
urlpatterns = default_urlpatterns(CosinnusOauthClientProvider)


urlpatterns += [
    path('social/connections/', custom_connections, name='socialaccount_connections'),
    path('password/set/', custom_password_set, name='account_set_password'),
    path('social/welcome/', welcome_oauth, name='welcome_oauth'),
    # social/signup/ is used in the OpenID Connect flow
    path('social/signup/', signup, name='socialaccount_signup'),
    # include openid_connect urls
    path('', include('allauth.socialaccount.providers.openid_connect.urls')),
]
