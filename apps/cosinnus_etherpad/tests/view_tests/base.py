# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
from django.contrib.auth.models import User
from django.test import TestCase, Client
from uuid import uuid4

from cosinnus.models import CosinnusGroup


class ViewTestCase(TestCase):

    def setUp(self, *args, **kwargs):
        super(ViewTestCase, self).setUp(*args, **kwargs)
        self.client = Client()
        self.group = CosinnusGroup.objects.create(
            name='testgroup-' + str(uuid4()), public=True)
        self.credential = 'admin'
        self.admin = User.objects.create_superuser(
            username=self.credential, email=None, password=self.credential)

    def tearDown(self, *args, **kwargs):
        # explicitly need to delete object, otherwise signals won't be fired
        # and group on server will persist
        self.group.delete()
        super(ViewTestCase, self).tearDown(*args, **kwargs)
