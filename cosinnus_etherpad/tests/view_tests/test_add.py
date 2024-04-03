# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse

from cosinnus_etherpad.models import Etherpad
from cosinnus_etherpad.tests.view_tests.base import ViewTestCase


class AddTest(ViewTestCase):

    def setUp(self, *args, **kwargs):
        super(AddTest, self).setUp(*args, **kwargs)
        self.kwargs = {'group': self.group.slug}
        self.url = reverse('cosinnus:etherpad:list', kwargs=self.kwargs)

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

    def test_post_logged_in(self):
        """
        Should return 302 to pad detail on successful POST and have a pad
        with given title
        """
        self.client.login(username=self.credential, password=self.credential)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        title = 'testpad'
        params = {
            'title': title,
        }
        response = self.client.post(self.url, params)
        self.assertEqual(response.status_code, 302)

        # do not catch exception here
        pad = Etherpad.objects.get(title=title)
        kwargs = {'group': self.group.slug, 'slug': pad.slug}
        self.assertIn(
            reverse('cosinnus:etherpad:pad-edit', kwargs=kwargs),
            response.get('location'))

        # explicitly need to delete object, otherwise signals won't be fired
        # and pad on server will persist
        pad.delete()
