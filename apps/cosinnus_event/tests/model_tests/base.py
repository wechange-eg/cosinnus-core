# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils.timezone import now

from cosinnus.models import CosinnusGroup
from cosinnus_event.models import Event


class ModelTestCase(TestCase):

    def setUp(self, *args, **kwargs):
        super(ModelTestCase, self).setUp(*args, **kwargs)
        self.group = CosinnusGroup.objects.create(name='testgroup')
        self.admin = User.objects.create_superuser(
            username='admin', email=None, password=None)
        self.now = now()
        self.event = Event.objects.create(
            group=self.group,
            creator=self.admin,
            title='testevent',
            from_date=self.now,
            to_date=self.now,
            state=Event.STATE_SCHEDULED)
