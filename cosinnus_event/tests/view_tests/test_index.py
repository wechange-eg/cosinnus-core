# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse

from cosinnus_event.tests.view_tests.base import ViewTestCase


class IndexTest(ViewTestCase):
    def test_index(self):
        """
        Should redirect to list view
        """
        kwargs = {'group': self.group.slug}
        url = reverse('cosinnus:event:index', kwargs=kwargs)
        self.client.force_login(self.admin)
        response = self.client.get(url)

        # should redirect to list view
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('cosinnus:event:list', kwargs=kwargs), response.get('location'))
