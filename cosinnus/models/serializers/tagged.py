# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import serializers


__all__ = ('TagListSerializer', )


class TagListSerializer(serializers.WritableField):
    # from http://pypede.wordpress.com/2013/07/06/using-django-rest-framework-with-tagged-items-django-taggit/

    def from_native(self, data):
        if not isinstance(data, (list, tuple)):
            raise ValueError("Expected a list of data")
        return data

    def to_native(self, obj):

        def quote_string(tag):
        # adapted from taggit.utils.edit_string_for_tags
            name = tag.name
            return ('"%s"' % name) if (',' in name or ' ' in name) else name

        if not isinstance(obj, (list, tuple)):
            return list(map(quote_string, obj.all()))
        return obj
