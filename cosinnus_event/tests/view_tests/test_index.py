# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse

from cosinnus_event.tests.view_tests.base import ViewTestCase


class IndexTest(ViewTestCase):
    def test_index(self):
        """
        Should show list view
        """
        kwargs = {'group': self.group.slug}
        url = reverse('cosinnus:event:index', kwargs=kwargs)
        self.client.force_login(self.admin)
        response = self.client.get(url)

        # there should be no redirect
        self.assertEqual(response.status_code, 200)

        # the url should match the list view
        self.assertEqual(reverse('cosinnus:event:list', kwargs=kwargs), url)
