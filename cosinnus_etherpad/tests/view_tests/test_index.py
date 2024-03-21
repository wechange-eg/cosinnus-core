# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse

from cosinnus_etherpad.tests.view_tests.base import ViewTestCase


class IndexTest(ViewTestCase):

    def test_index(self):
        """
        Should permanently redirect to list view
        """
        self.client.login(username=self.credential, password=self.credential)
        kwargs = {'group': self.group.slug}
        url = reverse('cosinnus:etherpad:index', kwargs=kwargs)
        response = self.client.get(url)

        # should redirect to list view
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse('cosinnus:etherpad:list', kwargs=kwargs),
            response.get('location'))
