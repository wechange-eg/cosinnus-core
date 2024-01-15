# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.test import TestCase, Client

from cosinnus.models import (CosinnusGroup, CosinnusGroupMembership)
from cosinnus.models.membership import MEMBERSHIP_MEMBER
from cosinnus.models.tagged import BaseTagObject


class ViewTestCase(TestCase):

    def setUp(self, *args, **kwargs):
        super(ViewTestCase, self).setUp(*args, **kwargs)
        self.client = Client()
        self.group = CosinnusGroup.objects.create(name='testgroup', public=True)
        self.group.media_tag.visibility = BaseTagObject.VISIBILITY_ALL
        self.group.media_tag.save()
        self.credential = 'admin'
        self.admin = User.objects.create_superuser(
            username=self.credential, email='admin@example.com', password=self.credential)

    def add_user(self, credential):
        self.user = User.objects.create_user(
            username=credential, password=credential, email=f'{credential}@example.com')
        CosinnusGroupMembership.objects.create(
            user=self.user,
            group=self.group,
            status=MEMBERSHIP_MEMBER
        )
        return self.user
