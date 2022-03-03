# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse

from cosinnus_todo.models import TodoEntry
from tests.view_tests.base import ViewTestCase


class AssignTest(ViewTestCase):

    def setUp(self, *args, **kwargs):
        super(AssignTest, self).setUp(*args, **kwargs)
        self.todo = TodoEntry.objects.create(
            group=self.group, title='testtodo', creator=self.admin)
        self.kwargs = {'group': self.group.slug, 'slug': self.todo.slug}
        self.url = reverse('cosinnus:todo:entry-assign', kwargs=self.kwargs)

    def test_get_not_logged_in(self):
        """
        Should return 403 on GET if not logged in
        """
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_get_logged_in(self):
        """
        Should return 200 on GET and have pad title set to readonly in form
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
        Should return 302 to detail page on successful POST todo entry should
        be assigned
        """
        self.client.login(username=self.credential, password=self.credential)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        params = {
            'csrfmiddlewaretoken': response.cookies['csrftoken'].value,
            'assigned_to': self.admin.pk,
        }
        response = self.client.post(self.url, params)
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse('cosinnus:todo:entry-detail', kwargs=self.kwargs),
            response.get('location'))
        todo = TodoEntry.objects.get(pk=self.todo.pk)
        self.assertEqual(todo.assigned_to, self.admin)

    def test_assign_invalid(self):
        credential = 'test'
        self.add_user(credential)
        self.client.login(username=credential, password=credential)
        response = self.client.get(self.url, follow=True)
        self.assertEqual(response.status_code, 200)

        kwargs = {'group': self.group.slug}
        list_url = reverse('cosinnus:todo:list', kwargs=kwargs)
        self.assertRedirects(response, list_url)
