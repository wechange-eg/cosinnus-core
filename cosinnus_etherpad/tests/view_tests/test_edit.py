# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse

from cosinnus_etherpad.models import Etherpad
from cosinnus_etherpad.tests.view_tests.base import ViewTestCase


class EditTest(ViewTestCase):
    def setUp(self, *args, **kwargs):
        super(EditTest, self).setUp(*args, **kwargs)
        self.pad = Etherpad.objects.create(group=self.group, title='testpad', creator=self.admin)
        self.kwargs = {'group': self.group.slug, 'slug': self.pad.slug}
        self.url = reverse('cosinnus:etherpad:pad-edit', kwargs=self.kwargs)

    def tearDown(self, *args, **kwargs):
        # be nice to remote server and delete pad also there
        self.pad.delete()
        super(EditTest, self).tearDown(*args, **kwargs)

    def test_get_not_logged_in(self):
        """
        Should return a redirect on GET if not logged in
        """
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

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
        Should return a redirect on POST if not logged in
        """
        self.client.logout()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)

    def test_post_logged_in(self):
        """
        Should return 302 to detail page on successful POST and have tag
        saved to pad
        """
        self.client.login(username=self.credential, password=self.credential)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        edited_description = 'Edited Description'
        self.assertNotEqual(self.pad.description, edited_description)
        params = {
            'title': self.pad.title,
            'description': edited_description,
        }
        response = self.client.post(self.url, params)
        self.assertEqual(response.status_code, 302)
        kwargs = {'group': self.group.slug, 'slug': self.pad.slug}
        self.assertIn(reverse('cosinnus:etherpad:pad-write', kwargs=kwargs), response.get('location'))
        self.pad.refresh_from_db()
        self.assertEqual(self.pad.description, edited_description)
