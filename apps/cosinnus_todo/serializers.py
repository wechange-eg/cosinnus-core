# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from rest_framework import serializers

from cosinnus_todo.models import TodoEntry, TodoList
from cosinnus.api.serializers.base import DateTimeL10nField
from cosinnus.api.serializers.group import GroupSimpleSerializer
from cosinnus.api.serializers.user import UserSerializer


class TodoListSerializer(serializers.ModelSerializer):
    item_count = serializers.IntegerField(source='item_count', read_only=True)

    class Meta(object):
        model = TodoList
        fields = ('id', 'title', 'group', 'slug', 'item_count')


class TodoEntrySerializer(serializers.ModelSerializer):
    group = GroupSimpleSerializer(many=False)

    created = DateTimeL10nField()
    creator = UserSerializer(many=False)

    #tags = TagListSerializer()

    todolist = TodoListSerializer(many=False, required=False)

    assigned_to = UserSerializer(many=False, required=False)
    due_date = DateTimeL10nField()

    completed_by = UserSerializer(many=False, required=False)
    completed_date = DateTimeL10nField()

    class Meta(object):
        model = TodoEntry
        fields = (
            'id', 'slug', 'title', 'group', 'created', 'creator',
            'note', 'priority', 'todolist',
            'assigned_to', 'due_date',
            'is_completed', 'completed_by', 'completed_date',
        )
