# The views used below are normally mapped in django.contrib.admin.urls.py
# This URLs file is used to provide a reliable view deployment for test purposes.
# It is also provided as a convenience to those who want to deploy these URLs
# elsewhere.

from django.conf.urls import url, include
from django.urls import path
from cosinnus.templatetags.cosinnus_tags import is_integrated_portal,\
    is_sso_portal
from cosinnus.forms.user import UserEmailLoginForm
from cosinnus.views.user import SetInitialPasswordView,\
    CosinnusPasswordResetConfirmView
from cosinnus.views import common, sso, user, integrated
from django.contrib.auth.views import PasswordChangeDoneView,\
    PasswordResetDoneView, PasswordResetConfirmView, PasswordResetCompleteView

# regular auth URLs, disabled for integrated portals
if not is_integrated_portal():

    # app_name = "cosinnus-auth"

    urlpatterns = [
        url(r'^login/$',
            common.cosinnus_login,
            name='login'),
        url(r'^logout/$',
            common.cosinnus_logout,
            {'next_page': '/'},
            name='logout'),
    ]
    
    # password change URLs are disabled for SSO-Portals
    if not is_sso_portal():
        urlpatterns += [
            url(r'^password_change/$',
                user.password_change_proxy,
                {'template_name': 'cosinnus/registration/password_change_form.html'},
                name='password_change'),
            url(r'^password_change/done/$',
                PasswordChangeDoneView.as_view(template_name='cosinnus/registration/password_change_done.html'),
                name='password_change_done'),
        ]
        
        urlpatterns += [
            url(r'^password_reset/$',
                user.password_reset_proxy,
                {
                    'template_name': 'cosinnus/registration/password_reset_form.html',
                    'email_template_name': 'cosinnus/registration/password_reset_email_16.html',
                },
                name='password_reset')
        ]
        
        urlpatterns += [
            url(r'^password_reset/done/$',
                PasswordResetDoneView.as_view(template_name='cosinnus/registration/password_reset_done.html'),
                name='password_reset_done')
        ]
        
        urlpatterns += [
            path('reset/<uidb64>/<token>/',
                 CosinnusPasswordResetConfirmView.as_view(template_name='cosinnus/registration/password_reset_confirm.html'),
                 name='password_reset_confirm')
        ]
        
        urlpatterns += [
            url(r'^reset/done/$',
                PasswordResetCompleteView.as_view(template_name='cosinnus/registration/password_reset_complete.html'),
                name='password_reset_complete'),
        ]

        # set initial password
        urlpatterns += [
            url(r'password_set_initial/', include([
                url(r'^$',
                    SetInitialPasswordView.as_view(
                        template_name='cosinnus/registration/password_set_initial_form.html'),
                    name='password_set_initial'),
                url('(?P<token>[0-9A-Za-z_\-]+)$',
                    SetInitialPasswordView.as_view(
                        template_name='cosinnus/registration/password_set_initial_form.html'),
                    name='password_set_initial'),
                ])),
        ]

# integrated portal auth patterns
if is_integrated_portal():
    urlpatterns = [
        url(r'^integrated/login/$', integrated.login_integrated, name='login-integrated'),
        url(r'^integrated/logout/$', integrated.logout_integrated, name='logout-integrated'),
        url(r'^integrated/create_user/$', integrated.create_user_integrated, name='create-user-integrated'),
    ]
    
# sso-only auth URLs
if is_sso_portal():
    urlpatterns += [
        url(r'^sso/login/$', sso.login, name='sso-login'),
        url(r'^sso/callback/$', sso.callback, name='sso-callback'),
        url(r'^sso/error/$', sso.error, name='sso-error'),
    ]
    