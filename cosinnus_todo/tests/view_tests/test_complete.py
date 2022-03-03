# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse
from django.utils.timezone import now, localtime

from cosinnus_todo.models import TodoEntry
from tests.view_tests.base import ViewTestCase


class CompleteTest(ViewTestCase):

    def setUp(self, *args, **kwargs):
        super(CompleteTest, self).setUp(*args, **kwargs)
        self.url = reverse('cosinnus:todo:entry-complete', kwargs=self.kwargs)

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
        be completeed
        """
        self.client.login(username=self.credential, password=self.credential)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        fmt = '%Y-%m-%d'
        completed_date = now().strftime(fmt)
        params = {
            'csrfmiddlewaretoken': response.cookies['csrftoken'].value,
            'completed_by': self.admin.pk,
            'completed_date': completed_date,
        }
        response = self.client.post(self.url, params)
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse('cosinnus:todo:entry-detail', kwargs=self.kwargs),
            response.get('location'))
        todo = TodoEntry.objects.get(pk=self.todo.pk)
        self.assertEqual(todo.completed_by, self.admin)
        self.assertEqual(localtime(todo.completed_date).strftime(fmt),
            completed_date)
