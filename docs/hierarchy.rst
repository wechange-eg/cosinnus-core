================================
Hierarchical Object Organisation
================================

A guide to add hierarchical object organisation to a cosinnus app.
The system is currently rather simple:

* Containers can be created and objects can be put into them.
* Containers can be nested infinitely within containers.
* Containers can be edited, although only their name can be changed.
* Containers are essentially the same as objects with the attribute is_container set to True.
* Objects or containers can not yet be moved between each other.

For an example implementation, have a look at the app `cosinnus_document`.


Extend Model
============

Import `BaseHierarchicalTaggableObjectModel` and extend it:

.. sourcecode:: python

    from cosinnus.models import BaseHierarchicalTaggableObjectModel

    class Model(BaseHierarchicalTaggableObjectModel):
        pass

Since `BaseHierarchicalTaggableObjectModel` is an abstract model, a migration
for the app model needs to be created and run:

.. sourcecode:: bash

   $ ./manage.py schemamigration cosinnus_app --auto
   $ ./manage.py migrate cosinnus_app


Add URLs
========

In the app's ``urls.py`` add the following URLs like this:

.. sourcecode:: python

   cosinnus_group_patterns += patterns(
       url(r'^add-container/$', 'container_add_view', name='container-add'),
       url(r'^(?P<slug>[^/]+)/add/$', 'object_add_view', name='object-add'),
       url(r'^(?P<slug>[^/]+)/add-container/$',
           'container_add_view', name='container-add'),
   )

The first URL will hook the view to add a container to the object root into
the URLconfig. The other URLs hook the views to add containers and objects to
other containers into the config.


View to add a container
=======================

In the app's ``views.py`` import ``AddContainerView`` from core:

.. sourcecode:: python

   from cosinnus.views.hierarchy import AddContainerView

Implement the model-specific container view:

.. sourcecode:: python

    class ModelAddContainerView(AddContainerView):
        model = model
        appname = 'appname'

        def form_valid(self, form):
            """Add model-specific attributes to form.instance"""
            form.instance.created_by = self.request.user
            return super(ModelAddContainerView, self).form_valid(form)

   container_add_view = ModelAddContainerView.as_view()

* ``model`` defines the model to add container objects for
* ``appname`` defines the name of the app to be used for reversing URLs.


Mixin the hierarchy tree
========================

The list view should add the `HierarchyTreeMixin` to its base classes. This
would give you a method `get_tree` to get a hierarchical tree of the
objects given as its argument:


.. sourcecode:: python

    from cosinnus.views.mixins.tagged import HierarchyTreeMixin

    class ModelListView(RequireReadMixin, FilterGroupMixin, TaggedListMixin,
                       SortableListMixin, HierarchyTreeMixin, ListView):
        model = model

        def get_context_data(self, *args, **kwargs):
            context = super(ModelListView, self).get_context_data(**kwargs)
            tree = self.get_tree(self.object_list)
            context.update({'tree': tree})
            return context

The `tree` in the context can be used in a list view template like this:

.. sourcecode:: html+django

    <div class="media-list">
      <div class="media">
      {% with node=tree tree_template="cosinnus_app/tree.html" %}
        {% include tree_template %}
      {% endwith %}
      </div>
    </div>

With the template `tree.html` looking like that:


.. sourcecode:: html+django

    {% load i18n cosinnus_tags %}

    <a class="pull-left" href="#">
        <!-- enter js to collapse containers here. -->
        <span class="glyphicon glyphicon-folder-open"></span>
    </a>

    {% if container.container_object %}
    <div class="media-body">
      <!-- regular container -->
      {% if user.is_superuser or user|is_group_admin:object %}
      <div class="btn-group pull-right" >
          <a class="btn btn-primary btn-mini" href="{% url 'cosinnus:app:object-add' group=group.slug slug=container.container_object.slug %}"><span class="glyphicon glyphicon-plus"></span>{% trans "Add object" %}</a>
          <a class="btn btn-primary btn-mini" href="{% url 'cosinnus:app:container-add' group=group.slug slug=container.container_object.slug %}"><span class="glyphicon glyphicon-plus"></span> {% trans "Create container" %}</a>
          <a class="btn btn-primary btn-mini dropdown-toggle" data-toggle="dropdown" href="#"><span class="caret"></span></a>
          <ul class="dropdown-menu">
              <li><a href="{% url 'cosinnus:app:object-edit' group=group.slug slug=container.container_object.slug %}"><span class="glyphicon glyphicon-pencil"></span> {% trans "Edit" %}</a></li>
              <li><a href="{% url 'cosinnus:app:object-delete' group=group.slug slug=container.container_object.slug %}"><span class="glyphicon glyphicon-trash"></span> {% trans "Delete" %}</a></li>
          </ul>
      </div>
      {% endif %}
      <p>
          {{ container.container_object.title }}
      </p>
    {% else %}
      <!-- root container -->
      {% if user.is_superuser or user|is_group_admin:object %}
      <div class="btn-group pull-right" >
          <a class="btn btn-primary btn-mini" href="{% url 'cosinnus:app:object-add' group=group.slug %}"><span class="glyphicon glyphicon-plus"></span> {% trans "Add object" %}</a>
          <a class="btn btn-primary btn-mini" href="{% url 'cosinnus:app:container-add' group=group.slug %}"><span class="glyphicon glyphicon-plus"></span> {% trans "Create container" %}</a>
      </div>
      {% endif %}
      <p>
          // {% trans "ROOT" %} //
      </p>
    {% endif %}


    {% if node.containers %}
      {% for container in node.containers %}
      <div class="media">
        {% with node=container %}
          {% include tree_template %}
        {% endwith %}
      </div>
      {% endfor %}
    {% endif %}

    {% if node.objects %}
      {% for object in node.objects %}
      <div class="media">
        <a class="pull-left" href="{{ object.get_absolute_url }}">
          <span class="glyphicon glyphicon-file"></span>
        </a>

        <span><a href="{{ object.get_absolute_url }}" title="{{ object.title }}">{{ object.title }}{% endif %}</a></span>

        <div class="btn-group pull-right">
            <a class="btn btn-primary btn-mini" href="{{ object.get_absolute_url }}"><span class="glyphicon glyphicon-eye-open"></span> {% trans "Show" %}</a>
            {% if user.is_superuser or user|is_group_member:object %}
            <a class="btn btn-primary btn-mini dropdown-toggle" data-toggle="dropdown" href="#"><span class="caret"></span></a>
            <ul class="dropdown-menu" role="menu">
              <li><a href="{% url 'cosinnus:app:object-edit' group=group.slug slug=object.slug %}"><span class="glyphicon glyphicon-pencil"></span> {% trans "Edit" %}</a></li>
              <li><a href="{% url 'cosinnus:app:object-delete' group=group.slug slug=object.slug %}"><span class="glyphicon glyphicon-trash"></span> {% trans "Delete" %}</a></li>
            </ul>
            {% endif %}
        </div>
      </div>
      {% endfor %}
    {% endif %}


If a list template shown as above is used, it is advisable to link a CSS file,
e.g. `static/css/cosinnus_app.css` which defines a few rules which will prevent
the dropdown menu from being clipped:

.. sourcecode:: css

	.media, .media-body {
		overflow: visible;
	}
	.media .media-body {
		display: table-cell;
		width: 10000px;
		*width: auto;
		*zoom: 1;
	}
	.media:before, .media:after {
		content: "";
		display: table;
	}
	.media:after {
		clear: both;
	}


Mixin the hierarchy path
========================

The add/edit views should add the `HierarchyPathMixin` to its base classes.
This will set up the object's path in the hierarchy appropriately.

.. sourcecode:: python

    from cosinnus.views.mixins.tagged import HierarchyPathMixin

    class ModelFormMixin(RequireWriteMixin, FilterGroupMixin,
        GroupFormKwargsMixin, HierarchyPathMixin):
        [...]


Mixin the hierarchy deletion
============================

The delete view should add the `HierarchyDeleteMixin` to its base classes.
This will delete containers and all objects contained within them.

.. sourcecode:: python

    from cosinnus.views.mixins.tagged import HierarchyDeleteMixin

    class ModelDeleteView(ModelFormMixin, HierarchyDeleteMixin, DeleteView):
        message_success = None
        message_error = None
        [...]

The app's `ModelFormMixin` might define a mechanism to emit error or
success messages. Since the `HierarchyDeleteMixin` will also emit these kind
of messages, it might be advisable to suppress the messages emitted via the
`ModelFormMixin`, hence setting `message_success` and `message_error` to
`None` in the example above.

The template for the delete view might then look like this:

.. sourcecode:: html+django

    <form action="" method="post" class="form-horizontal">
      {% csrf_token %}
      <div class="control-group">
        <label class="control-label">
          {% if object.is_container %}
            <h3>{% trans "Are you sure you want to delete this container and all objects in it?" %}</h3>
          {% else %}
            <h3>{% trans "Are you sure you want to delete this object?" %}</h3>
          {% endif %}
        </label>

        <input type="hidden" name="objects_to_delete" value="{{ objects_to_delete }}" />
        <div>
             <div class="well well-sm">
              {% for obj in objects_to_delete %}
                {% if obj.is_container %}
                  <span class="glyphicon glyphicon-folder-open"></span>
                {% else %}
                  <span class="glyphicon glyphicon-file"></span>
                {% endif %}
                <span><a href="{% url 'cosinnus:app:object-detail' group=group.slug slug=obj.slug %}" title="{{ obj.title }}">{{ obj.title }}</a></span>
                <span>{{ obj.path }}</span>
                {% if not forloop.last %}<br/>{% endif %}
              {% endfor %}
            </div>
        </div>

        <div class="controls">
          <button type="submit" class="btn btn-danger">
            {% trans "Delete" %}
          </button>
          <a href="{% url 'cosinnus:app:list' group=group.slug %}" class="btn">
            {% trans "Cancel" %}
          </a>
        </div>
      </div>
    </form>

The app is good to go now, have fun organising your app objects!
