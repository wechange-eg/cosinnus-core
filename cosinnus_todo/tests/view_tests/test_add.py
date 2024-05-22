# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse

from cosinnus_todo.models import PRIORITY_LOW, TodoEntry
from cosinnus_todo.tests.view_tests.base import ViewTestCase


class AddTest(ViewTestCase):
    def setUp(self, *args, **kwargs):
        super(AddTest, self).setUp(*args, **kwargs)
        self.kwargs = {'group': self.group.slug, 'listslug': 'general'}
        self.url = reverse('cosinnus:todo:entry-add', kwargs=self.kwargs)

    def test_get_not_logged_in(self):
        """
        Should return a redirect on GET if not logged in
        """
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_get_logged_in(self):
        """
        Should return 200 on GET when logged in
        """
        self.client.login(username=self.credential, password=self.credential)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_not_logged_in(self):
        """
        Should return a redirect on POST if not logged in
        """
        self.client.logout()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('next=' + self.url, response['Location'])

    def test_post_logged_in(self):
        """
        Should return 302 to detail page on successful POST and have a todo
        with given title
        """
        self.client.login(username=self.credential, password=self.credential)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        title = 'testtodo1'
        params = {
            'title': title,
            'priority': PRIORITY_LOW,
            'assigned_to': self.admin.pk,
        }
        response = self.client.post(self.url, params)
        self.assertEqual(response.status_code, 302)

        # do not catch exception here
        todo = TodoEntry.objects.get(title=title)
        kwargs = {'group': self.group.slug, 'listslug': 'general', 'todoslug': todo.slug}
        self.assertIn(reverse('cosinnus:todo:todo-in-list-list', kwargs=kwargs), response.get('location'))
        self.assertEqual(todo.priority, PRIORITY_LOW)
        self.assertEqual(todo.creator, self.admin)
        self.assertEqual(todo.group, self.group)
