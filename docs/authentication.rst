==============
Authentication
==============

Cosinnus as such doesn't provide an authentication system. It has been tested
with Django's contrib auth system which could be hooked in like this:

URLs
====

The following could be added to a project's ``urls.py``:

.. code-block:: python

   urlpatterns += patterns('django.contrib.auth.views',
       url(r'^', include('cosinnus.utils.django_auth_urls')),
   )


Templates
=========

Cosinnus provides a few templates to suit Django's authentication system which
can be found in ``cosinnus/registration/``. But a specific project might
need its own look and feel, so the URL config can be changed accordingly to
meet the project's requirements.
