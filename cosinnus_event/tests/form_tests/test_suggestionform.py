# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils.timezone import now

from bootstrap3_datetime.widgets import DateTimePicker

from cosinnus.models import CosinnusGroup
from cosinnus_event.forms import SuggestionForm
from cosinnus_event.models import Event, Suggestion


class SuggestionFormTest(TestCase):

    def test_has_datetimepicker_widgets(self):
        """
        Should have DateTimePicker widgets for from_date and to_date
        """
        group = CosinnusGroup.objects.create(name='testgroup')
        credential = 'admin'
        admin = User.objects.create_superuser(
            username=credential, email=None, password=credential)
        event = Event.objects.create(group=group,
            creator=admin, public=True, title='testevent')
        Suggestion.objects.create(
            event=event, from_date=now(), to_date=now())

        form = SuggestionForm()
        self.assertIsInstance(form.fields['from_date'].widget, DateTimePicker)
