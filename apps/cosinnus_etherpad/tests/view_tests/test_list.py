# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
from django.urls import reverse

from cosinnus_etherpad.models import Etherpad
from tests.view_tests.base import ViewTestCase


class ListTest(ViewTestCase):

    def test_list_not_logged_in(self):
        """
        Should return 200 if not logged in
        """
        kwargs = {'group': self.group.slug}
        url = reverse('cosinnus:etherpad:list', kwargs=kwargs)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_list_logged_in_admin(self):
        """
        Should return 200 and contain URL to add a pad if admin
        """
        self.client.login(username=self.credential, password=self.credential)
        kwargs = {'group': self.group.slug}
        url = reverse('cosinnus:etherpad:list', kwargs=kwargs)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            reverse('cosinnus:etherpad:pad-add', kwargs=kwargs),
            str(response.content))  # type byte in Python3.3

    def test_filtered_invalid_tag(self):
        """
        Should return 404 on invalid tag
        """
        kwargs = {'group': self.group.slug, 'tag': 'foo'}
        url = reverse('cosinnus:etherpad:list-filtered', kwargs=kwargs)

        # should return 404
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_filtered_valid_tag(self):
        """
        Should return 200 on valid tag and URL to edit pad
        """
        tag = 'foo'
        pad = Etherpad.objects.create(group=self.group, title='testpad')
        pad.tags.add(tag)
        kwargs = {'group': self.group.slug, 'tag': tag}
        url = reverse('cosinnus:etherpad:list-filtered', kwargs=kwargs)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        kwargs = {'group': self.group.slug, 'slug': pad.slug}
        self.assertIn(
            reverse('cosinnus:etherpad:pad-detail', kwargs=kwargs),
            str(response.content))  # type byte in Python3.3

        # be nice to remote server and delete pad also there
        pad.delete()
