# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse

from cosinnus_event.models import Event
from cosinnus_event.tests.view_tests.base import ViewTestCase


class AddTest(ViewTestCase):

    def setUp(self, *args, **kwargs):
        super(AddTest, self).setUp(*args, **kwargs)
        self.kwargs = {'group': self.group.slug}
        self.url = reverse('cosinnus:event:event-add', kwargs=self.kwargs)

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
        Should return 403 on POST if not logged in
        """
        self.client.logout()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)

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
            'from_date_0': '2014-01-01',
            'from_date_1': '00:00',
            'to_date_0': '2014-01-01',
            'to_date_1': '23:00',
            'video_conference_type': Event.NO_VIDEO_CONFERENCE,
        }
        response = self.client.post(self.url, params)
        self.assertEqual(response.status_code, 302)

        # do not catch exception here
        event = Event.objects.get(title=title)
        kwargs = {'group': self.group.slug, 'slug': event.slug}
        self.assertIn(
            reverse('cosinnus:event:event-detail', kwargs=kwargs),
            response.get('location'))
        # set by EntryAddView.form_valid
        self.assertEqual(event.creator, self.admin)
        self.assertEqual(event.group, self.group)
