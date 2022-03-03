# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
from django.test import TestCase
from uuid import uuid4

from cosinnus.models import CosinnusGroup
from cosinnus_etherpad.managers import EtherpadManager
from cosinnus_etherpad.models import Etherpad


class EtherpadManagerTest(TestCase):

    def setUp(self):
        super(EtherpadManagerTest, self).setUp()
        self.group = CosinnusGroup.objects.create(
            name='testgroup-' + str(uuid4()))
        self.pad = Etherpad.objects.create(
            group=self.group, title='testpad')

    def tearDown(self):
        # explicitly need to delete object, otherwise signals won't be fired
        # and pad/group on server will persist
        self.pad.delete()
        self.group.delete()
        super(EtherpadManagerTest, self).tearDown()

    def test_tags(self):
        tags = ['foo', 'bar']
        for tag in tags:
            self.pad.tags.add(tag)
        manager = EtherpadManager()
        self.assertEqual(manager.tags(), tags)
