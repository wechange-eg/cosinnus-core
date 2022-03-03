# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse

from tests.view_tests.base import ViewTestCase


class IndexTest(ViewTestCase):

    def test_index(self):
        """
        Should permanently redirect to list view
        """
        kwargs = {'group': self.group.slug}
        url = reverse('cosinnus:event:index', kwargs=kwargs)
        response = self.client.get(url)

        # should redirect to list view
        self.assertEqual(response.status_code, 301)
        self.assertIn(
            reverse('cosinnus:event:list', kwargs=kwargs),
            response.get('location'))
