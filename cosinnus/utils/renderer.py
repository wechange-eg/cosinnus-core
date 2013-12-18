# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.template.loader import render_to_string


class BaseRenderer(object):

    @classmethod
    def get_template(cls):
        if not hasattr(cls, 'template'):
            from django.core.exceptions import ImproperlyConfigured
            raise ImproperlyConfigured('Missing template definition for '
                'renderer %s' % cls.__name__)
        return cls.template

    @classmethod
    def render(cls, context, **kwargs):
        context.update(kwargs)
        return render_to_string(cls.get_template(), context)


"""
An example renderer for a specific app could be::

    from cosinnus.utils.renderer import BaseRenderer

    class MyRenderer(BaseRenderer):

        template = "path/to/template.html"

        @classmethod
        def render(cls, context, myobjs):
            return super(MyRenderer, cls).render(context, myobjs=myobjs)
"""
