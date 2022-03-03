# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse

from cosinnus_event.models import Event
from tests.view_tests.base import ViewTestCase


class AddTest(ViewTestCase):

    def setUp(self, *args, **kwargs):
        super(AddTest, self).setUp(*args, **kwargs)
        self.kwargs = {'group': self.group.slug}
        self.url = reverse('cosinnus:event:entry-add', kwargs=self.kwargs)

    def test_get_not_logged_in(self):
        """
        Should return 403 on GET if not logged in
        """
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_get_logged_in(self):
        """
        Should return 200 on GET when logged in
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
        Should return 302 to detail page on successful POST and have an event
        with given title
        """
        self.client.login(username=self.credential, password=self.credential)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        title = 'testevent2'
        params = {
            'title': title,
            'suggestions-TOTAL_FORMS': '1',
            'suggestions-INITIAL_FORMS': '0',
            'suggestions-MAX_NUM_FORMS': '1000',
            'suggestions-0-from_date': '2014-01-01',
            'suggestions-0-to_date': '2014-01-02',
        }
        response = self.client.post(self.url, params)
        self.assertEqual(response.status_code, 302)

        # do not catch exception here
        event = Event.objects.get(title=title)
        self.assertEqual(len(event.suggestions.all()), 1)
        kwargs = {'group': self.group.slug, 'slug': event.slug}
        self.assertIn(
            reverse('cosinnus:event:entry-detail', kwargs=kwargs),
            response.get('location'))
        # set by EntryAddView.form_valid
        self.assertEqual(event.creator, self.admin)
        self.assertEqual(event.group, self.group)
