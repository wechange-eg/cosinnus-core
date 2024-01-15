# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse

from cosinnus_todo.tests.view_tests.base import ViewTestCase


class IndexTest(ViewTestCase):

    def test_index(self):
        """
        Should permanently redirect to list view
        """
        kwargs = {'group': self.group.slug}
        self.client.login(username=self.credential, password=self.credential)
        url = reverse('cosinnus:todo:index', kwargs=kwargs)
        response = self.client.get(url)

        # should redirect to list view
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse('cosinnus:todo:list', kwargs=kwargs),
            response.get('location'))
