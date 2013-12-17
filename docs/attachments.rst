=========================
Attached Cosinnus Objects
=========================

A guide to enabling attached objects for a cosinnus app. Use this to let users link Cosinnus objects to other Cosinnus objects. Want to show related News post and a Flyer on your event page? Attach Cosinnus-Note and Cosinnus-File to Cosinnus-Events! Want to attach a discussion etherpad to a Wiki page? You got it!

"I want to enable attaching objects to my cosinnus app's Model"
---------------------------------------------------------------

* In your app settings.COSINNUS_ATTACHABLE_OBJECTS add an entry for your cosinnus model, with a list of the cosinnus models you want to be able to be attached. 
  * Example: We want to be able to attach Files and Notes to Wiki pages ():
  * ``COSINNUS_ATTACHABLE_OBJECTS = {'cosinnus_wiki.Page' : ['cosinnus_file.FileEntry', 'cosinnus_note.Note'], }``
* Put this template tag in your object's view template to show attached objects in your Model's view:
  * ``{% cosinnus_render_attached_objects object %}`` where <object> is the instance of your viewed object
  * This will automatically render all objects attached to the wiki page.
  * Don't forget to add ``{% load cosinnus_tags %}`` to your template
  * If you want to check beforehand if there are attached objects that will be rendered, do it like this: ``{% if object.attached_objects.all %}``
* We also need to modifiy your object's create and update view, so that Objects can actually be attached:
  * In your views.py, import ``from cosinnus.views.attached_object import CreateViewAttachable, UpdateViewAttachable`` 
    * let your custom CreateView extend ``CreateViewAttachable`` instead of ``CreateView``
    * let your custom UpdateView extend ``UpdateViewAttachable`` instead of ``UpdateView``
  * In your forms.py, import ``from cosinnus.forms.attached_object import FormAttachable`` 
    * let your custom object Form extend ``FormAttachable`` instead of ``ModelForm``

"I want to provide a Model that can be attached to other Cosinnus Objects"
--------------------------------------------------------------------------

To offer your objects as attachable object inside the cosinnus apps, you need to follow these steps: 

1) Create a renderer (and probably a template) for displaying your object when it is attached to some other cosinnus object. You only need to implement and declare the renderer. Cosinnus-core handles calling and using it to render your object at runtime, from any other cosinnus app.
2) Declare your objects as attachable_objects in your cosinnus_app.py file.

Create a renderer for the Model you want to provide
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* This renderer is being passed the full list of attached cosinnus objects of your model's type at request time. It is expected to return rendered html code of your file type to be displayed at the view of a cosinnus object (if this object has any objects of your type attached).
  * An example for cosinnus_file's FileEntry: ( in cosinnus_file.renderer.py )::
  
    class FileEntryRenderer(object):
        @staticmethod
        def render_attached_objects(context, files):
            template="cosinnus_file/attached_files.html"
            context['files'] = files
            return render_to_string(template, context)


  * The template for your attached files could look like this:  ( in cosinnus_file/attached_files.html )::

    <div class="media-body"> 
        {% for file in files %} 
        <div> 
            Behold an attached file! with the slug <b>{{ file.slug }}</b>: <a href="{% url 'cosinnus:file:download' group=group.slug slug=file.slug %}">{{ file.sourcefilename }}</a>
        </div>
    </div>

Declare your cosinnus object as attachable object
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* In your cosinnus_app.py, define the two following properties (substitute your model name and the renderer you have created::

    ATTACHABLE_OBJECT_MODELS = ['FileEntry']
    ATTACHABLE_OBJECT_RENDERERS = {'FileEntry':renderer.FileEntryRenderer}


* In your django.po localization file, add a label for the Form field for your attached files in the syntax: ``attached:<app_name>.<model_name>``. Example::

    msgid "attached:cosinnus_file.FileEntry"
    msgstr "Angehängte Dateien"


You're done! Cosinnus-Core should now pick up your attachable object and use your renderer to display objects of your model's type!