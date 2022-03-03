# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse
from django.utils.timezone import now, localtime

from cosinnus_todo.models import TodoEntry, PRIORITY_LOW
from tests.view_tests.base import ViewTestCase


class EditTest(ViewTestCase):

    def setUp(self, *args, **kwargs):
        super(EditTest, self).setUp(*args, **kwargs)
        self.todo = TodoEntry.objects.create(
            group=self.group, title='testtodo', creator=self.admin)
        self.kwargs = {'group': self.group.slug, 'slug': self.todo.slug}
        self.url = reverse('cosinnus:todo:entry-edit', kwargs=self.kwargs)

    def test_get_not_logged_in(self):
        """
        Should return 403 on GET if not logged in
        """
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_get_logged_in(self):
        """
        Should return 200 on GET and have todo title set to readonly in form
        when logged in
        """
        self.client.login(username=self.credential, password=self.credential)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_not_logged_in(self):
        """
        Should return 403 on POST if not logged in
        """
        self.client.logout()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)

    def test_post_logged_in(self):
        """
        Should return 302 to detail page on successful POST and have tag
        saved to todo
        """
        self.client.login(username=self.credential, password=self.credential)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        tag = 'Fän©µ-Tæg'  # Test unicode handling
        fmt = '%Y-%m-%d'
        completed_date = now().strftime(fmt)
        params = {
            'title': self.todo.title,
            'priority': PRIORITY_LOW,
            'tags': tag,
            'completed_by': self.admin.pk,
            'completed_date': completed_date,
        }
        response = self.client.post(self.url, params)
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse('cosinnus:todo:entry-detail', kwargs=self.kwargs),
            response.get('location'))
        num_tags = len(self.todo.tags.filter(name=tag))
        self.assertEqual(num_tags, 1)

        todo = TodoEntry.objects.get(pk=self.todo.pk)
        self.assertEqual(todo.priority, PRIORITY_LOW)
        self.assertEqual(todo.creator, self.admin)
        self.assertEqual(todo.group, self.group)
        self.assertEqual(todo.completed_by, self.admin)
        self.assertEqual(localtime(todo.completed_date).strftime(fmt),
            completed_date)

    def test_assigned_to_invalid(self):
        credential = 'test'
        self.add_user(credential)
        self.client.login(username=credential, password=credential)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        params = {
            'title': self.todo.title,
            'priority': PRIORITY_LOW,
            'assigned_to': self.user.pk,
        }
        response = self.client.post(self.url, params)
        self.assertEqual(response.status_code, 200)
        self.assertIn('assigned_to', response.context['form']['obj'].errors)
