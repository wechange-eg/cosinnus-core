===============
API Integration
===============

*Cosinnus* and some of its apps provide a RESTful API to interact with the
underlying data. This API is used by e.g. the Ajax HTML widgets. Since API
design is hard and *Cosinnus* core cannot guarantee to always offer the same
API versions as the different apps, the apps have to take care of using common
URL paths. However, *Cosinnus* core does offer a convenient method that can be
used to automatically include the app name and group patterns in the URL.


URLs
====

Defining the URL patterns
-------------------------

.. currentmodule:: cosinnus.utils.urls

In an app's ``urls.py`` add a variable ``cosinnus_api_patterns`` that is
defined as:

.. code-block:: python

    cosinnus_api_patterns = api_patterns(1, 'myapp', False, 'myapp.views',
        url(r'^path/to/view/$', 'some_view', name='some-api-view'),
    )

The resulting URL path will be (relative to the overall include)::

    /api/v1/myapp/path/to/view/

If you need group patterns, (e.g. group slug in the URL), set the 3rd argument
in :func:`api_patterns` to ``True``:

.. code-block:: python

    cosinnus_api_patterns = api_patterns(1, 'myapp', True, 'myapp.views',
        url(r'^path/to/view/$', 'some_view', name='some-api-view'),
    )

The resulting URL path will be (relative to the overall include)::

    /api/v1/group/GROUP_SLUG_PATTERN/myapp/path/to/view/

If you need multiple versions, group the patterns by versions and adjust the 1st
argument:

.. code-block:: python

    cosinnus_api_patterns = api_patterns(4, 'myapp', True, 'myapp.views',
        url(r'^path/to/view/$', 'some_view', name='some-api-view'),
    )
    cosinnus_api_patterns += api_patterns(5, 'myapp', True, 'myapp.views',
        url(r'^path/to/view/$', 'some_view_new', name='some-api-view_new'),
    )

The resulting URL paths will be (relative to the overall include)::

    /api/v4/myapp/path/to/view/
    /api/v5/myapp/path/to/view/

Furthermore, remember to append the ``cosinnus_api_patterns`` to the
``urlpatterns``:

.. code-block:: python

    urlpatterns += cosinnus_api_patterns


Registering the URL patterns
----------------------------

To let *Cosinnus* know about the URL pattern, you need to register them at the
:class:`~cosinnus.core.registries.urls.URLRegistry`. This is done analogously to the
root and group url patterns:

.. code-block:: python

    from cosinnus.core.registries import url_registry
    from myapp.urls import (cosinnus_api_patterns,
       cosinnus_group_patterns, cosinnus_root_patterns)

    url_registry.register('myapp', cosinnus_root_patterns,
        cosinnus_group_patterns, cosinnus_api_patterns)

You can also tell *Cosinnus* to automatically discover the URL patterns from a
given URLConf. *Cosinnus* will look for the given attributes imported above on
its own:

.. code-block:: python

    from cosinnus.core.registries import url_registry

    url_registry.register_urlconf('myapp', 'myapp.urls')


Using the API URL definitions
-----------------------------

The normal *Cosinnus* URLs don't include the API URLs for various reasons. One
of them is the lack of flexibility, e.g. if you want your API URLs to be on a
different domain. Hence you have to explicitly include them in your projects
``ROOT_URLCONF``:

.. code-block:: python

    from django.conf.urls import patterns, include, url

    from cosinnus.core.registries import url_registry

    urlpatterns = patterns('',
        # ...
        # url(r'^', include('cosinnus.urls', namespace='cosinnus')),
        # ...
        url(r'^', include(url_registry.api_urlpatterns, namespace='cosinnus-api')),
        # ...
    )
