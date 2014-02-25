# The views used below are normally mapped in django.contrib.admin.urls.py
# This URLs file is used to provide a reliable view deployment for test purposes.
# It is also provided as a convenience to those who want to deploy these URLs
# elsewhere.

from django.conf.urls import patterns, url

urlpatterns = patterns('',
    url(r'^login/$',
        'django.contrib.auth.views.login',
        {'template_name': 'cosinnus/registration/login.html'},
        name='login'),
    url(r'^logout/$',
        'django.contrib.auth.views.logout',
        {'template_name': 'cosinnus/registration/logged_out.html'},
        name='logout'),
    url(r'^password_change/$',
        'django.contrib.auth.views.password_change',
        {'template_name': 'cosinnus/registration/password_change_form.html'},
        name='password_change'),
    url(r'^password_change/done/$',
        'django.contrib.auth.views.password_change_done',
        {'template_name': 'cosinnus/registration/password_change_done.html'},
        name='password_change_done'),
    url(r'^password_reset/$',
        'django.contrib.auth.views.password_reset',
        {
            'template_name': 'cosinnus/registration/password_reset_form.html',
            'email_template_name': 'cosinnus/registration/password_reset_email.html',
        },
        name='password_reset'),
    url(r'^password_reset/done/$',
        'django.contrib.auth.views.password_reset_done',
        {'template_name': 'cosinnus/registration/password_reset_done.html'},
        name='password_reset_done'),
    url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        'django.contrib.auth.views.password_reset_confirm',
        {'template_name': 'cosinnus/registration/password_reset_confirm.html'},
        name='password_reset_confirm'),
    url(r'^reset/done/$',
        'django.contrib.auth.views.password_reset_complete',
        {'template_name': 'cosinnus/registration/password_reset_complete.html'},
        name='password_reset_complete'),
)
