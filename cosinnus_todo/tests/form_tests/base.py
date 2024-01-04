# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils.timezone import now

from cosinnus.models import (CosinnusGroup, CosinnusGroupMembership)
from cosinnus.models.membership import MEMBERSHIP_MEMBER, MEMBERSHIP_ADMIN
from cosinnus_todo.models import TodoEntry


class FormTestCase(TestCase):

    def setUp(self, *args, **kwargs):
        super(FormTestCase, self).setUp(*args, **kwargs)
        self.group = CosinnusGroup.objects.create(name='testgroup')
        self.admin = User.objects.create_superuser(
            username='admin', email='admin@example.com', password=None, last_login=now())
        self.admin.cosinnus_profile.settings['tos_accepted'] = True
        self.admin.cosinnus_profile.save()
        CosinnusGroupMembership.objects.create(user=self.admin,
            group=self.group, status=MEMBERSHIP_ADMIN)
        self.todo = TodoEntry.objects.create(
            group=self.group, title='testtodo', creator=self.admin)


    def add_user(self, credential):
        self.user = User.objects.create_user(
            username=credential, password=credential, email=f'{credential}@example.com')
        CosinnusGroupMembership.objects.create(
            user=self.user,
            group=self.group,
            status=MEMBERSHIP_MEMBER
        )
        return self.user
