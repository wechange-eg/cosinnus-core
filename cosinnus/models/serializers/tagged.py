# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from rest_framework import serializers


__all__ = ('TagListSerializer', )


class TagListSerializer(serializers.ReadOnlyField):
    # from http://pypede.wordpress.com/2013/07/06/using-django-rest-framework-with-tagged-items-django-taggit/

    def _quote_string(self, tag):
        # adapted from taggit.utils.edit_string_for_tags
        name = tag.name
        return ('"%s"' % name) if (',' in name or ' ' in name) else name

    def from_native(self, data):
        """
        Deserialize primitives -> objects.
        """
        if isinstance(data, (list, tuple)):
            return ', '.join(map(self._quote_string, data))
        elif isinstance(data, six.text_type):
            return data
        raise ValueError("Expected a list of data")

    def to_native(self, obj):
        """
        Serialize objects -> primitives.
        """
        if not isinstance(obj, (list, tuple)):
            return ', '.join(map(self._quote_string, obj.all()))
        return obj
