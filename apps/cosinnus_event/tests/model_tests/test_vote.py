# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.utils.encoding import force_text

from cosinnus_event.models import Suggestion, Vote, localize
from tests.model_tests.base import ModelTestCase


class VoteTest(ModelTestCase):

    def setUp(self):
        super(VoteTest, self).setUp()
        self.suggestion = Suggestion.objects.create(
            from_date=self.now, to_date=self.now, event=self.event)
        self.vote = Vote.objects.create(
            suggestion=self.suggestion, voter=self.admin)

    def test_string_repr(self):
        """
        Should have certain string representation
        """
        expected = 'Vote for %(event)s: %(from)s - %(to)s' % {
            'event': self.suggestion.event.title,
            'from': localize(self.suggestion.from_date, 'd. F Y h:i'),
            'to': localize(self.suggestion.to_date, 'd. F Y h:i'),
        }
        self.assertEqual(expected, force_text(self.vote))

    def test_post_vote_delete(self):
        """
        Suggestion should have decreased count after vote has been deleted
        """
        self.assertEqual(self.suggestion.count, 1)
        self.vote.delete()
        self.assertEqual(self.suggestion.count, 0)

    def test_post_vote_save(self):
        """
        Suggestion should have increased count after vote has been created
        """
        self.assertEqual(self.suggestion.count, 1)
        user = User.objects.create(
            username='user', email='user', password='user')
        Vote.objects.create(suggestion=self.suggestion, voter=user)
        self.assertEqual(self.suggestion.count, 2)
