# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from rest_framework import serializers

from cosinnus.models.group import CosinnusGroup


__all__ = ('GroupSimpleSerializer', )


class GroupSimpleSerializer(serializers.ModelSerializer):

    class Meta(object):
        model = CosinnusGroup
        fields = ('id', 'name', 'slug', 'public', 'description', )
