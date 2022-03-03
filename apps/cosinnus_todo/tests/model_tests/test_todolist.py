# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.test import TransactionTestCase

from cosinnus.models import CosinnusGroup
from cosinnus_todo.models import TodoEntry, TodoList


class TodoListTest(TransactionTestCase):

    def setUp(self):
        super(TodoListTest, self).setUp()
        self.group = CosinnusGroup.objects.create(name='testgroup')
        self.user = User.objects.create(username='user', email='user@localhost')

    def test_delete_no_todos(self):
        self.assertEqual(TodoList.objects.all().count(), 0)
        l = TodoList.objects.create(title='List 1', group=self.group)
        self.assertEqual(TodoList.objects.all().count(), 1)
        l.delete()
        self.assertEqual(TodoList.objects.all().count(), 0)

    def test_delete(self):
        self.assertEqual(TodoList.objects.all().count(), 0)
        self.assertEqual(TodoEntry.objects.all().count(), 0)
        l = TodoList.objects.create(title='List 2', group=self.group)
        TodoEntry.objects.create(title='TD 1', group=self.group, creator=self.user, todolist=l)
        TodoEntry.objects.create(title='TD 2', group=self.group, creator=self.user, todolist=l)
        self.assertEqual(TodoList.objects.all().count(), 1)
        self.assertEqual(TodoEntry.objects.all().count(), 2)
        l.delete()
        self.assertEqual(TodoList.objects.all().count(), 0)
        self.assertEqual(TodoEntry.objects.all().count(), 0)
