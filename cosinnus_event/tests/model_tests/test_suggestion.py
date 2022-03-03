# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import timedelta
from django.utils.encoding import force_text
from django.utils.timezone import now

from cosinnus_event.models import Suggestion, Vote, localize
from tests.model_tests.base import ModelTestCase


class SuggestionTest(ModelTestCase):

    def setUp(self):
        super(SuggestionTest, self).setUp()
        self.suggestion = Suggestion.objects.create(
            from_date=self.now, to_date=self.now, event=self.event)

    def test_string_repr_scheduled_single_day(self):
        """
        Should have certain string representation if single day suggestion
        """
        expected = '%(date)s - %(end)s (%(count)d)' % {
            'date': localize(self.suggestion.from_date, 'd. F Y H:i'),
            'end': localize(self.suggestion.to_date, 'H:i'),
            'count': self.suggestion.count,
        }
        self.assertEqual(expected, force_text(self.suggestion))

    def test_string_repr_scheduled_multi_day(self):
        """
        Should have certain string representation if multi day suggestion
        """
        self.suggestion.to_date += timedelta(days=1)
        self.suggestion.save()
        expected = '%(from)s - %(to)s (%(count)d)' % {
            'from': localize(self.suggestion.from_date, 'd. F Y H:i'),
            'to': localize(self.suggestion.to_date, 'd. F Y H:i'),
            'count': self.suggestion.count,
        }
        self.assertEqual(expected, force_text(self.suggestion))

    def test_single_day_same_day(self):
        """
        Should be single day suggestion if from and to date are on the same day
        """
        self.suggestion.from_date = self.suggestion.to_date
        self.suggestion.save()
        self.assertTrue(self.suggestion.single_day)

    def test_single_day_different_day(self):
        """
        Should not be single day suggestion if from and to date are on
        different days
        """
        self.suggestion.from_date = now()
        self.suggestion.to_date = self.suggestion.from_date + timedelta(days=1)
        self.suggestion.save()
        self.assertFalse(self.suggestion.single_day)

    def test_update_vote_count(self):
        """
        Should update the vote count
        """
        self.assertEqual(self.suggestion.count, 0)

        # Can't test directly, due to use of RelatedManager to Vote and signals
        # being sent on vote create/delete
        vote = Vote.objects.create(suggestion=self.suggestion, voter=self.admin)
        self.assertEqual(self.suggestion.count, 1)

        vote.delete()
        self.assertEqual(self.suggestion.count, 0)
