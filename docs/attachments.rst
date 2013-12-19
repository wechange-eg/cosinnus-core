=========================
Attached Cosinnus Objects
=========================

A guide to enabling attached objects for a cosinnus app. Use this to let users
link Cosinnus objects to other Cosinnus objects. Want to show related News post
and a Flyer on your event page? Attach Cosinnus-Note and Cosinnus-File to
Cosinnus-Events! Want to attach a discussion etherpad to a Wiki page? You got
it!


Enable attaching objects to a cosinnus app's Model
==================================================

In your app ``settings.COSINNUS_ATTACHABLE_OBJECTS`` add an entry for your
cosinnus model, with a list of the cosinnus models you want to be able to be
attached.

.. note:: Example: We want to be able to attach Files and Notes to Wiki pages:
    
   .. sourcecode:: python

      COSINNUS_ATTACHABLE_OBJECTS = {
          'cosinnus_wiki.Page' : [
              'cosinnus_file.FileEntry',
              'cosinnus_note.Note',
          ],
      }


Show attached objects in a template
===================================

In a template use the ``cosinnus_render_attached_objects`` template tag show
attached objects in for the given object. This will automatically render all
objects attached to the object.

At the top of the template load the ``cosinnus_tags``:

.. sourcecode:: html+django

   {% load cosinnus_tags %}

Then, at the position where you want to render the objects, add:

.. sourcecode:: html+django

   {% cosinnus_render_attached_objects object %}

where ``object`` is the instance of the object whos attachments to show.

If you want to check beforehand if there are attached objects that will be
rendered, do it like this:

.. sourcecode:: html+django

   {% if object.attached_objects.all %}
     {% cosinnus_render_attached_objects object %}
   {% endif %}


Add attached objects
====================

To be able to attach other cosinnus objects, you need to modifiy your object's
form views (``MyModelCreateView``, ``MyModelUpdateView``, etc.), so that objects
can actually be attached

.. currentmodule:: cosinnus.views.attached_object

Let your create views inherit from :py:class:`CreateViewAttachable` and your
update views inherit from :py:class:`UpdateViewAttachable`.


.. currentmodule:: cosinnus.forms.attached_object

To add the appropriate functionality to the underlying forms, make your model
form inherit from :py:class:`FormAttachable`.


Create a Model that can be attached to other objects
====================================================

To offer your objects as attachable object inside the cosinnus apps, you need
to follow these steps: 

1. Create a renderer (and probably a template) for displaying your object when
   it is attached to some other cosinnus object. You only need to implement and
   declare the renderer. Cosinnus-core handles calling and using it to render
   your object at runtime, from any other cosinnus app.
2. Declare your objects as attachable_objects in your cosinnus_app.py file.

Create a renderer for the Model you want to provide
---------------------------------------------------

* This renderer is being passed the full list of attached cosinnus objects of
  your model's type at request time. It is expected to return rendered html
  code of your file type to be displayed at the view of a cosinnus object (if
  this object has any objects of your type attached).

  * An example for cosinnus_file's FileEntry: (in cosinnus_file.renderer.py):
  
    .. sourcecode:: python

       class FileEntryRenderer(object):
           @staticmethod
           def render_attached_objects(context, files):
               template="cosinnus_file/attached_files.html"
               context['files'] = files
               return render_to_string(template, context)


  * The respective template could be like this:

    .. sourcecode:: html+django

       <div class="media-body">
         {% for file in files %}
           <div> 
             Behold an attached file! with the slug <b>{{ file.slug }}</b>: <a href="{% url 'cosinnus:file:download' group=group.slug slug=file.slug %}">{{ file.sourcefilename }}</a>
           </div>
       </div>

Declare your cosinnus object as attachable object
-------------------------------------------------

* In your cosinnus_app.py, define the two following properties (substitute your
  model name and the renderer you have created:

  .. sourcecode:: python

     ATTACHABLE_OBJECT_MODELS = ['FileEntry']
     ATTACHABLE_OBJECT_RENDERERS = {'FileEntry':renderer.FileEntryRenderer}

* In your django.po localization file, add a label for the Form field for your
  attached files in the syntax: ``attached:<app_name>.<model_name>``. Example:

  .. sourcecode:: po

    msgid "attached:cosinnus_file.FileEntry"
    msgstr "Angehängte Dateien"

You're done! Cosinnus-Core should now pick up your attachable object and use
your renderer to display objects of your model's type!
