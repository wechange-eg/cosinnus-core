==============
Authentication
==============

Cosinnus as such doesn't provide an authentication system. It has been tested
with Django's contrib auth system which could be hooked in like this:

URLs
====

The following could be added to a project's urls.py:

.. sourcecode:: python

	urlpatterns += patterns('django.contrib.auth.views',
		url(r'^login/$',
			'login',
			{'template_name':'cosinnus/registration/login.html'},
			name='login'),
		url(r'^logout/$',
			'logout',
			{'template_name':'cosinnus/registration/logged_out.html'},
			name='logout'),
		url(r'^password_change/$',
			'password_change',
			name='password_change'),
		url(r'^password_change/done/$',
			'password_change_done',
			name='password_change_done'),
		url(r'^password_reset/$',
			'password_reset',
			{'template_name':'cosinnus/registration/password_reset_form.html'},
			name='password_reset'),
		url(r'^password_reset/done/$',
			'password_reset_done',
			{'template_name':'cosinnus/registration/password_reset_done.html'},
			name='password_reset_done'),
		# uidb36 < 1.6
		url(r'^password_reset/confirm/(?P<uidb36>[0-9A-Za-z]{1,13})-(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
			'password_reset_confirm',
			{'template_name':'cosinnus/registration/password_reset_confirm.html'},
			name='password_reset_confirm'),
		# uidb64 >= 1.6
		url(r'^password_reset/confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>.+)/$',
			'password_reset_confirm',
			{'template_name':'cosinnus/registration/password_reset_confirm.html'},
			name='password_reset_confirm'),
		url(r'^password_reset/complete$',
			'password_reset_complete',
			{'template_name':'cosinnus/registration/password_reset_complete.html'},
			name='password_reset_complete'),
	)


Templates
=========

Cosinnus provides a few templates to suit Django's authentication system which
can be found in ``cosinnus/registration/`` . But a specific project might
need its own look and feel, so the URL config can be changed accordingly to
meet the project's requirements.
