# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse

from cosinnus_todo.models import TodoEntry
from tests.view_tests.base import ViewTestCase


class DeleteTest(ViewTestCase):

    def setUp(self, *args, **kwargs):
        super(DeleteTest, self).setUp(*args, **kwargs)
        self.url = reverse('cosinnus:todo:entry-delete', kwargs=self.kwargs)

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
        Should return 302 to list page on successful POST and have todo deleted
        """
        self.client.login(username=self.credential, password=self.credential)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        params = {
            'csrfmiddlewaretoken': response.cookies['csrftoken'].value,
        }
        response = self.client.post(self.url, params)
        self.assertEqual(response.status_code, 302)
        kwargs = {'group': self.group.slug}
        self.assertIn(
            reverse('cosinnus:todo:list', kwargs=kwargs),
            response.get('location'))
        self.assertEqual(len(TodoEntry.objects.all()), 0)
