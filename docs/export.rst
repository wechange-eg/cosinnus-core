========================
Export Cosinnus App Data
========================

A guide to implement text data export for a cosinnus app. The exported data
will be offered by the application server as a downloadable file.

Add a new URL
=============

In your app's ``urls.py`` add a URL with name ``export``, e.g.:

.. sourcecode:: python

   cosinnus_group_patterns += patterns(
      url(r'^export/$', 'export_view', name='export'),
   )

Now cosinnus core's group export view will pick up your app automatically.
Although the actual export will still fail, because you haven't defined an
``export_view`` yet.


Add an export view
==================

In the app's ``views.py`` import ``JSONExportView`` from core and define the
view:

.. sourcecode:: python

   from cosinnus.views.export import JSONExportView
   class AppExportView(JSONExportView):
       fields = [
           'model_field0',
           'model_field1',
       ]
       model = AppModel
       file_prefix = 'cosinnus_appname'
   export_view = AppExportView.as_view()

* ``fields`` defines the model fields you want in your exported data
* ``model`` defines the model where to lookup the fields
* ``file_prefix`` defines the prefix for the JSON file to be downloaded,
  probably should be the same as your app's name.


Add an export button
====================

You might want to have an export button next to the add button on your list
page.You could add it like this in ``templates/<appname>/<appmodel>_list.html``

.. sourcecode:: html+django

   {% load cosinnus_tags %}
   {% if user.is_superuser or user|is_group_admin:object %}
     <li class="active"><a href="{% url 'cosinnus:app:export' group=group.slug %}" class="btn"><span class="glyphicon glyphicon-export"></span> {% trans "Export" context "the verb" %}</a></li>
   {% endif %}


You're done, the app will neatly export its data in JSON format now!
