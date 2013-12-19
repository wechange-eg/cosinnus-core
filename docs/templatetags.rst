===================================
Template Tags Bundled With Cosinnus
===================================

.. currentmodule:: cosinnus.templatetags.cosinnus_tags

Cosinnus provides several templatetags one can use in templates.


Autocompletion for form fields
==============================

Cosinnus uses `Bootstrap 3 Typeahead`_ to provide a autocompletion list. To use
it, only a few things have to be done:

1. Make sure to return an iterable of strings that will be used as choices:

   .. sourcecode:: python

      def get_context_data(self, **kwargs):
          ctx = super(MyView, self).get_context_data(**kwargs)
          ctx['tags'] = MyModel.objects.tags()
          return ctx

2. In the template, include load the ``cosinnus_tags`` and ``static`` templatetags:

   .. sourcecode:: html+django

      {% load cosinnus_tags %}
      {% load static from staticfiles %}

3. Next, include the typeahead JS:

   * Make sure to include the ``{{ block.super }}`` call to not override
     previously defined JS.
   * Include the reference to ``bootstrap3-typeahead.min.js`` only the first
     time
   
   .. sourcecode:: html+django

      {% block extrafooter %}
        {{ block.super }}
        <script type="text/javascript" src="{% static "js/vendor/bootstrap3-typeahead.min.js" %}"></script>
        {% cosinnus_autocomplete '#id_name' tags %}
      {% endblock extrafooter %}

   ``{% cosinnus_autocomplete '#id_name' tags %}`` takes a jQuery selector as
   first argument to define the field it should work on. The second argument is
   an iterator returning strings.


.. _Bootstrap 3 Typeahead: https://github.com/bassjobsen/Bootstrap-3-Typeahead
