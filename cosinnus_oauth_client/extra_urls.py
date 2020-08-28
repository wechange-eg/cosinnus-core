from django.conf.urls import url

from cosinnus_oauth_client.views import custom_connections
from cosinnus_oauth_client.views import custom_password_set
from cosinnus_oauth_client.views import welcome_oauth

urlpatterns = [
    url(r'social/connections/$', custom_connections, name='socialaccount_connections'),
    url(r'password/set/', custom_password_set, name='account_set_password'),
    url(r'welcome/', welcome_oauth, name='welcome_oauth'),
]
