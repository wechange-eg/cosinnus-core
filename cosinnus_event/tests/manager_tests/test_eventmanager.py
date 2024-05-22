# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils.timezone import now

from cosinnus.models import CosinnusGroup
from cosinnus_event.models import Event


class EventManagerTest(TestCase):
    def setUp(self):
        super(EventManagerTest, self).setUp()
        self.group = CosinnusGroup.objects.create(name='testgroup')
        self.admin = User.objects.create_superuser(username='admin', email=None, password=None)
        self.event = Event.objects.create(
            group=self.group, creator=self.admin, public=True, state=Event.STATE_SCHEDULED, title='testevent'
        )

    def test_public(self):
        """
        Should have public event if event public
        """
        self.event.media_tag.visibility = 2
        self.event.media_tag.save()
        self.assertEqual(self.event, Event.objects.public()[0])

    def test_public_non_public_event(self):
        """
        Should have no public event if event not public
        """
        self.event.media_tag.visibility = 0
        self.event.media_tag.save()
        self.assertListEqual([], list(Event.objects.public()))

    def test_public_canceled_event(self):
        """
        Should have no public event if event canceled
        """
        self.event.state = Event.STATE_CANCELED
        self.event.public = True
        self.event.save()
        self.assertListEqual([], list(Event.objects.public()))

    def test_upcoming_in_past(self):
        """
        Should have no upcoming events if event is in past
        """
        self.event.from_date = now() - timedelta(days=2)
        self.event.to_date = now() - timedelta(days=1)
        self.event.save()
        self.assertListEqual([], list(Event.objects.all_upcoming()))

    def test_upcoming_in_future(self):
        """
        Should have upcoming events if event is in future
        """
        self.event.from_date = now() + timedelta(days=1)
        self.event.to_date = now() + timedelta(days=2)
        self.event.save()
        self.assertEqual(self.event, Event.objects.all_upcoming()[0])
