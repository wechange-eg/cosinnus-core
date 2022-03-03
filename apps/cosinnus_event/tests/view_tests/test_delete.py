# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse
from django.utils.timezone import now

from cosinnus_event.models import Event
from tests.view_tests.base import ViewTestCase


class DeleteTest(ViewTestCase):

    def setUp(self, *args, **kwargs):
        super(DeleteTest, self).setUp(*args, **kwargs)
        self.event = Event.objects.create(
            group=self.group,
            creator=self.admin,
            public=True,
            title='testevent',
            from_date=now(),
            to_date=now(),
            state=Event.STATE_SCHEDULED)
        self.kwargs = {'group': self.group.slug, 'slug': self.event.slug}
        self.url = reverse('cosinnus:event:entry-delete', kwargs=self.kwargs)

    def test_get_not_logged_in(self):
        """
        Should return 403 on GET if not logged in
        """
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_get_logged_in(self):
        """
        Should return 200 on GET and have event title set to readonly in form
        when logged in
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
        Should return 302 to list page on successful POST and have event deleted
        """
        self.client.login(username=self.credential, password=self.credential)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        params = {
            'csrfmiddlewaretoken': response.cookies['csrftoken'].value,
        }
        response = self.client.post(self.url, params)
        self.assertEqual(response.status_code, 302)
        kwargs = {'group': self.group.slug}
        self.assertIn(
            reverse('cosinnus:event:list', kwargs=kwargs),
            response.get('location'))
        self.assertEqual(len(Event.objects.all()), 0)
