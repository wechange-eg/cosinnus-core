# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
from datetime import timedelta
from django.urls import reverse
from django.utils.encoding import force_text
from django.utils.timezone import now

from cosinnus_event.models import Event
from tests.view_tests.base import ViewTestCase


class ListTest(ViewTestCase):

    def test_list_not_logged_in(self):
        """
        Should return 200
        """
        kwargs = {'group': self.group.slug}
        url = reverse('cosinnus:event:list', kwargs=kwargs)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_list_logged_in_admin(self):
        """
        Should return 200 and contain URL to add an event
        """
        self.client.login(username=self.credential, password=self.credential)
        kwargs = {'group': self.group.slug}
        url = reverse('cosinnus:event:list', kwargs=kwargs)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            reverse('cosinnus:event:entry-add', kwargs=kwargs),
            str(response.content))  # type byte in Python3.3

    def test_list_past_future_events(self):
        """
        Should have past and future events in context
        """
        Event.objects.create(
            group=self.group,
            creator=self.admin,
            public=True,
            title='past testevent',
            from_date=now(),
            to_date=now(),
            state=Event.STATE_SCHEDULED)
        Event.objects.create(
            group=self.group,
            creator=self.admin,
            public=True,
            title='future testevent',
            from_date=now() + timedelta(days=1),
            to_date=now() + timedelta(days=1),
            state=Event.STATE_SCHEDULED)
        kwargs = {'group': self.group.slug}
        url = reverse('cosinnus:event:list', kwargs=kwargs)
        response = self.client.get(url)

        num_past_events = len(response.context['past_events'])
        self.assertEqual(num_past_events, 1)
        num_future_events = len(response.context['future_events'])
        self.assertEqual(num_future_events, 1)

    def test_filtered_invalid_tag(self):
        """
        Should return 404 on invalid tag
        """
        kwargs = {'group': self.group.slug, 'tag': 'foo'}
        url = reverse('cosinnus:event:list-filtered', kwargs=kwargs)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_filtered_valid_tag(self):
        """
        Should return 200 on valid tag and URL to edit event
        """
        tag = 'foo'
        event = Event.objects.create(
            group=self.group,
            creator=self.admin,
            public=True,
            title='past testevent',
            from_date=now(),
            to_date=now(),
            state=Event.STATE_SCHEDULED)
        event.tags.add(tag)
        kwargs = {'group': self.group.slug, 'tag': tag}
        url = reverse('cosinnus:event:list-filtered', kwargs=kwargs)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        kwargs = {'group': self.group.slug, 'slug': event.slug}
        self.assertIn(
            reverse('cosinnus:event:entry-detail', kwargs=kwargs),
            force_text(response.content))
