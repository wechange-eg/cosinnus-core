# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils.timezone import now

from cosinnus.models import CosinnusGroup
from cosinnus_event.forms import VoteForm
from cosinnus_event.models import Event, Suggestion


class VoteFormTest(TestCase):

    def setUp(self):
        super(VoteFormTest, self).setUp()
        self.group = CosinnusGroup.objects.create(name='testgroup')
        self.credential = 'admin'
        self.admin = User.objects.create_superuser(
            username=self.credential, email=None, password=self.credential)
        self.event = Event.objects.create(group=self.group,
            creator=self.admin, public=True, title='testevent')

    def test_label_if_suggestion(self):
        """
        Should have string representation of suggestion when calling get_label()
        if suggestion is given as initial
        """
        suggestion = Suggestion.objects.create(
            event=self.event, from_date=now(), to_date=now())
        initial = {'suggestion': suggestion.pk}
        form = VoteForm(initial=initial)
        self.assertEqual(form.get_label(), str(suggestion))

    def test_label_if_no_suggestion(self):
        """
        Should have empty string when calling get_label() if if no suggestion
        is given as initial
        """
        form = VoteForm()
        self.assertEqual(form.get_label(), '')
