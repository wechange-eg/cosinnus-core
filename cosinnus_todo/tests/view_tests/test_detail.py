# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse
from django.utils.encoding import force_str

from cosinnus_todo.models import TodoEntry, TodoList
from cosinnus_todo.tests.view_tests.base import ViewTestCase


class DetailTest(ViewTestCase):
    def test_detail(self):
        """
        Should return 200 and contain todo title
        """
        todo_list = TodoList.objects.first()
        todo = TodoEntry.objects.create(group=self.group, title='testtitle', creator=self.admin, todolist=todo_list)
        kwargs = {'group': self.group.slug, 'slug': todo.slug}
        url = reverse('cosinnus:todo:entry-detail', kwargs=kwargs)
        self.client.login(username=self.credential, password=self.credential)
        response = self.client.get(url)

        # should return 200
        self.assertEqual(response.status_code, 200)

        # content should contain pad title
        self.assertIn(todo.title, force_str(response.content))
