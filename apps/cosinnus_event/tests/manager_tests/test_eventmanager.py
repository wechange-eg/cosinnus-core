# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import range
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
        self.admin = User.objects.create_superuser(
            username='admin', email=None, password=None)
        self.event = Event.objects.create(group=self.group,
            creator=self.admin, public=True, state=Event.STATE_SCHEDULED,
            title='testevent')

    def test_tags(self):
        """
        Should have tags
        """
        tags = ['foo', 'bar']
        for tag in tags:
            self.event.tags.add(tag)
        self.assertEqual(Event.objects.tags(), tags)

    def test_public(self):
        """
        Should have public event if event public
        """
        self.event.public = True
        self.event.save()
        self.assertEqual(self.event, Event.objects.public()[0])

    def test_public_non_public_event(self):
        """
        Should have no public event if event not public
        """
        self.event.public = False
        self.event.save()
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
        self.assertListEqual([], list(Event.objects.upcoming(count=1)))

    def test_upcoming_in_future(self):
        """
        Should have upcoming events if event is in future
        """
        self.event.from_date = now() + timedelta(days=1)
        self.event.to_date = now() + timedelta(days=2)
        self.event.save()
        self.assertEqual(self.event, Event.objects.upcoming(count=1)[0])

    def test_upcoming_count_in_future(self):
        """
        Should have upcoming count events if event is in future
        """
        count = 3
        for i in range(1, count + 2):  # + 2 to get count+1 upcoming events
            Event.objects.create(
                group=self.group,
                creator=self.admin,
                public=True,
                title='testevent %d' % i,
                state=Event.STATE_SCHEDULED,
                from_date=now(),
                to_date=now() + timedelta(days=1))

        num_events = len(Event.objects.all())
        self.assertLess(count, num_events)

        num_upcoming_all = len(Event.objects.upcoming(count=num_events))
        num_upcoming_count = len(Event.objects.upcoming(count=count))
        self.assertLess(num_upcoming_count, num_upcoming_all)
