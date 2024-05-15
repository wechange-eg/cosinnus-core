# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
from uuid import uuid4

from django.test import TestCase

from cosinnus.models import CosinnusGroup
from cosinnus_etherpad.managers import EtherpadManager
from cosinnus_etherpad.models import Etherpad


class EtherpadManagerTest(TestCase):
    def setUp(self):
        super(EtherpadManagerTest, self).setUp()
        self.group = CosinnusGroup.objects.create(name='testgroup-' + str(uuid4()))
        self.pad = Etherpad.objects.create(group=self.group, title='testpad')

    def tearDown(self):
        # explicitly need to delete object, otherwise signals won't be fired
        # and pad/group on server will persist
        self.pad.delete()
        self.group.delete()
        super(EtherpadManagerTest, self).tearDown()
