# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
from datetime import timedelta

from django.urls import reverse
from django.utils.timezone import now

from cosinnus.models.tagged import BaseTagObject
from cosinnus_event.models import Event
from cosinnus_event.tests.view_tests.base import ViewTestCase


class ListTest(ViewTestCase):
    def test_list_not_logged_in(self):
        """
        Should return 200
        """
        kwargs = {'group': self.group.slug}
        url = reverse('cosinnus:event:list', kwargs=kwargs)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)

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
            reverse('cosinnus:event:event-add', kwargs=kwargs), str(response.content)
        )  # type byte in Python3.3

    def test_list_future_events(self):
        """
        Should have future events in context
        """
        event = Event.objects.create(
            group=self.group,
            creator=self.admin,
            title='future testevent',
            from_date=now() + timedelta(days=1),
            to_date=now() + timedelta(days=1),
            state=Event.STATE_SCHEDULED,
        )
        event.media_tag.visibility = BaseTagObject.VISIBILITY_ALL
        event.media_tag.save()
        kwargs = {'group': self.group.slug}
        self.client.login(username=self.credential, password=self.credential)
        url = reverse('cosinnus:event:list', kwargs=kwargs)
        response = self.client.get(url)
        num_future_events = len(response.context['future_events'])
        self.assertEqual(num_future_events, 1)
