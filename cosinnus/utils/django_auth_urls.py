# The views used below are normally mapped in django.contrib.admin.urls.py
# This URLs file is used to provide a reliable view deployment for test purposes.
# It is also provided as a convenience to those who want to deploy these URLs
# elsewhere.

import django

from django.conf.urls import patterns, url
from cosinnus.templatetags.cosinnus_tags import is_integrated_portal,\
    is_sso_portal
from cosinnus.forms.user import UserEmailLoginForm


# regular auth URLs, disabled for integrated portals
if not is_integrated_portal():
    
    urlpatterns = patterns('',
        url(r'^login/$',
            'cosinnus.views.common.cosinnus_login',
            {'template_name': 'cosinnus/registration/login.html',
             'authentication_form': UserEmailLoginForm},
            name='login'),
        url(r'^logout/$',
            'cosinnus.views.common.cosinnus_logout',
            {'next_page': '/'},
            name='logout'),
    )
    
    # password change URLs are disabled for SSO-Portals
    if not is_sso_portal():
        urlpatterns += patterns('',
            url(r'^password_change/$',
                'cosinnus.views.user.password_change_proxy',
                {'template_name': 'cosinnus/registration/password_change_form.html'},
                name='password_change'),
            url(r'^password_change/done/$',
                'django.contrib.auth.views.password_change_done',
                {'template_name': 'cosinnus/registration/password_change_done.html'},
                name='password_change_done'),
        )
        
        if django.VERSION[:2] >= (1, 6):
            urlpatterns += patterns('',
                url(r'^password_reset/$',
                    'cosinnus.views.user.password_reset_proxy',
                    {
                        'template_name': 'cosinnus/registration/password_reset_form.html',
                        'email_template_name': 'cosinnus/registration/password_reset_email_16.html',
                    },
                    name='password_reset')
            )
        else:
            urlpatterns += patterns('',
                url(r'^password_reset/$',
                    'cosinnus.views.user.password_reset_proxy',
                    {
                        'template_name': 'cosinnus/registration/password_reset_form.html',
                        'email_template_name': 'cosinnus/registration/password_reset_email_15.html',
                    },
                    name='password_reset')
            )
        
        urlpatterns += patterns('',
            url(r'^password_reset/done/$',
                'django.contrib.auth.views.password_reset_done',
                {'template_name': 'cosinnus/registration/password_reset_done.html'},
                name='password_reset_done')
        )
        
        if django.VERSION[:2] >= (1, 6):
            urlpatterns += patterns('',
                url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
                    'django.contrib.auth.views.password_reset_confirm',
                    {'template_name': 'cosinnus/registration/password_reset_confirm.html'},
                    name='password_reset_confirm')
            )
        else:
            urlpatterns += patterns('',
                url(r'^reset/(?P<uidb36>[0-9A-Za-z]{1,13})-(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
                    'django.contrib.auth.views.password_reset_confirm',
                    {'template_name': 'cosinnus/registration/password_reset_confirm.html'},
                    name='password_reset_confirm')
            )
        
        urlpatterns += patterns('',
            url(r'^reset/done/$',
                'django.contrib.auth.views.password_reset_complete',
                {'template_name': 'cosinnus/registration/password_reset_complete.html'},
                name='password_reset_complete'),
        )

# integrated portal auth patterns
if is_integrated_portal():
    urlpatterns = patterns('',
        url(r'^integrated/login/$', 'cosinnus.views.integrated.login_integrated', name='login-integrated'),
        url(r'^integrated/logout/$', 'cosinnus.views.integrated.logout_integrated', name='logout-integrated'),
        url(r'^integrated/create_user/$', 'cosinnus.views.integrated.create_user_integrated', name='create-user-integrated'),
    )
    
# sso-only auth URLs
if is_sso_portal():
    urlpatterns += patterns('cosinnus.views',
        url(r'^sso/login/$', 'sso.login', name='sso-login'),
        url(r'^sso/callback/$', 'sso.callback', name='sso-callback'),
        url(r'^sso/error/$', 'sso.error', name='sso-error'),
    )
    