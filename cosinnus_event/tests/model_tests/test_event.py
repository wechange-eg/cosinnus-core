# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import timedelta
from django.utils import dateformat
from django.utils.encoding import force_text
from django.utils.formats import date_format
from django.utils.timezone import now, localtime

from cosinnus_event.models import Event, Suggestion, localize
from tests.model_tests.base import ModelTestCase


class EventTest(ModelTestCase):

    def test_string_repr_scheduled_single_day(self):
        """
        Should have certain string representation if single day event
        """
        expected = '%(event)s (%(date)s - %(end)s)' % {
            'event': self.event.title,
            'date': localize(self.event.from_date, 'd. F Y h:i'),
            'end': localize(self.event.to_date, 'h:i'),
        }
        self.assertEqual(expected, force_text(self.event))

    def test_string_repr_scheduled_multi_day(self):
        """
        Should have certain string representation if multi day event
        """
        self.event.to_date += timedelta(days=1)
        self.event.save()
        expected = '%(event)s (%(from)s - %(to)s)' % {
            'event': self.event.title,
            'from': localize(self.event.from_date, 'd. F Y h:i'),
            'to': localize(self.event.to_date, 'd. F Y h:i'),
        }
        self.assertEqual(expected, force_text(self.event))

    def test_string_repr_pending(self):
        """
        Should have certain string representation if pending event
        """
        self.event.state = Event.STATE_VOTING_OPEN
        self.event.save()
        expected = '%(event)s (pending)' % {'event': self.event.title}
        self.assertEqual(expected, force_text(self.event))

    def test_set_suggestion_none(self):
        """
        Should not set suggestion if none is given to event
        """
        self.event.set_suggestion(sugg=None)
        self.assertEqual(self.event.suggestion, None)

    def test_set_suggestion(self):
        """
        Should set suggestion for an event
        """
        suggestion = Suggestion.objects.create(
            event=self.event, from_date=now(), to_date=now())
        self.event.set_suggestion(sugg=suggestion)
        self.assertEqual(self.event.suggestion, suggestion)

    def test_set_suggestion_other_event(self):
        """
        Should not set suggestion for another event
        """
        event = Event.objects.create(
            group=self.group,
            creator=self.admin,
            public=True,
            title='testevent')
        suggestion = Suggestion.objects.create(
            event=event, from_date=now(), to_date=now())
        self.event.set_suggestion(sugg=suggestion)
        self.assertEqual(self.event.suggestion, None)

    def test_single_day_same_day(self):
        """
        Should be single day event if from and to date are on the same day
        """
        self.event.from_date = self.event.to_date
        self.event.save()
        self.assertTrue(self.event.single_day)

    def test_single_day_different_day(self):
        """
        Should not be single day event if from and to date are on different days
        """
        self.event.from_date = now()
        self.event.to_date = self.event.from_date + timedelta(days=1)
        self.event.save()
        self.assertFalse(self.event.single_day)

    def test_period_same_day(self):
        """
        Period should be same as from date on same day
        """
        self.event.from_date = self.event.to_date
        self.event.save()
        expected = localize(self.event.from_date, 'd.m.Y')
        self.assertEqual(expected, self.event.get_period())

    def test_period_other_day(self):
        """
        Period should be a certain string on different from and to dates
        """
        self.event.from_date = now()
        self.event.to_date = self.event.from_date + timedelta(days=1)
        self.event.save()
        expected = '%s - %s' % (localize(self.event.from_date, 'd.m.'),
            localize(self.event.to_date, 'd.m.Y'))
        self.assertEqual(expected, self.event.get_period())

    def test_localize_no_format(self):
        """
        Localize should return a certain localtime date_format when no format
        string is given
        """
        format = None
        expected = date_format(localtime(self.event.from_date), format)
        self.assertEqual(expected, localize(self.event.from_date, format))

    def test_localize_datetime_format(self):
        """
        Localize should return a certain localtime date_format when a
        predefined format string is given
        """
        format = 'DATETIME_FORMAT'
        expected = date_format(localtime(self.event.from_date), format)
        self.assertEqual(expected, localize(self.event.from_date, format))

    def test_localize_custom_format(self):
        """
        Localize should return a certain localtime date_format when a
        custom format string is given
        """
        format = 'd.m'
        expected = dateformat.format(localtime(self.event.from_date), format)
        self.assertEqual(expected, localize(self.event.from_date, format))

    def test_public(self):
        """
        Public should be set to False per default
        """
        self.assertFalse(self.event.public)
