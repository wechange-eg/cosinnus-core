# The views used below are normally mapped in django.contrib.admin.urls.py
# This URLs file is used to provide a reliable view deployment for test purposes.
# It is also provided as a convenience to those who want to deploy these URLs
# elsewhere.

from django.contrib.auth.views import (
    PasswordChangeDoneView,
    PasswordResetCompleteView,
    PasswordResetDoneView,
)
from django.urls import include, path, re_path

from cosinnus.templatetags.cosinnus_tags import is_integrated_portal, is_sso_portal
from cosinnus.views import common, integrated, sso, user
from cosinnus.views.user import CosinnusPasswordResetConfirmView, SetInitialPasswordView

# regular auth URLs, disabled for integrated portals
if not is_integrated_portal():
    # app_name = "cosinnus-auth"

    urlpatterns = [
        path('login/', common.cosinnus_login, name='login'),
        path('logout/', common.cosinnus_logout, {'next_page': '/'}, name='logout'),
    ]

    # password change URLs are disabled for SSO-Portals
    if not is_sso_portal():
        urlpatterns += [
            path(
                'password_change/',
                user.password_change_proxy,
                {'template_name': 'cosinnus/registration/password_change_form.html'},
                name='password_change',
            ),
            path(
                'password_change/done/',
                PasswordChangeDoneView.as_view(template_name='cosinnus/registration/password_change_done.html'),
                name='password_change_done',
            ),
        ]

        urlpatterns += [
            path(
                'password_reset/',
                user.password_reset_proxy,
                {
                    'template_name': 'cosinnus/registration/password_reset_form.html',
                    'email_template_name': 'cosinnus/registration/password_reset_email_16.html',
                },
                name='password_reset',
            )
        ]

        urlpatterns += [
            path(
                'password_reset/done/',
                PasswordResetDoneView.as_view(template_name='cosinnus/registration/password_reset_done.html'),
                name='password_reset_done',
            )
        ]

        urlpatterns += [
            path(
                'reset/<uidb64>/<token>/',
                CosinnusPasswordResetConfirmView.as_view(
                    template_name='cosinnus/registration/password_reset_confirm.html'
                ),
                name='password_reset_confirm',
            )
        ]

        urlpatterns += [
            path(
                'reset/done/',
                PasswordResetCompleteView.as_view(template_name='cosinnus/registration/password_reset_complete.html'),
                name='password_reset_complete',
            ),
        ]

        # set initial password
        urlpatterns += [
            path(
                'password_set_initial/',
                include(
                    [
                        path(
                            '',
                            SetInitialPasswordView.as_view(
                                template_name='cosinnus/registration/password_set_initial_form.html'
                            ),
                            name='password_set_initial',
                        ),
                        re_path(
                            '(?P<token>[0-9A-Za-z_\-]+)/?$',
                            SetInitialPasswordView.as_view(
                                template_name='cosinnus/registration/password_set_initial_form.html'
                            ),
                            name='password_set_initial',
                        ),
                    ]
                ),
            ),
        ]

# integrated portal auth patterns
if is_integrated_portal():
    urlpatterns = [
        path('integrated/login/', integrated.login_integrated, name='login-integrated'),
        path('integrated/logout/', integrated.logout_integrated, name='logout-integrated'),
        path('integrated/create_user/', integrated.create_user_integrated, name='create-user-integrated'),
    ]

# sso-only auth URLs
if is_sso_portal():
    urlpatterns += [
        path('sso/login/', sso.login, name='sso-login'),
        path('sso/callback/', sso.callback, name='sso-callback'),
        path('sso/error/', sso.error, name='sso-error'),
    ]
