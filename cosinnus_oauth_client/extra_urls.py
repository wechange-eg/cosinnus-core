from django.urls import path

from cosinnus_oauth_client.views import custom_connections, custom_password_set, welcome_oauth

urlpatterns = [
    path('social/connections/', custom_connections, name='socialaccount_connections'),
    path('password/set/', custom_password_set, name='account_set_password'),
    path('welcome/', welcome_oauth, name='welcome_oauth'),
]
