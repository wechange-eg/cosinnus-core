# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest

import django

from django.contrib.auth.models import User
from django.test import TestCase

from cosinnus.models import (CosinnusGroup, CosinnusGroupMembership)
from cosinnus.models.membership import MEMBERSHIP_MEMBER
from cosinnus_message.models import Message


def _c(**kwargs):
    return Message.objects.create(**kwargs)


@unittest.skipIf(django.VERSION[:2] <= (1, 6) and django.VERSION[:2] >= (1, 8), 'backwards compat')
class Django16MethodRename(TestCase):

    def test_manager_has_get_query_set(self):
        self.assertTrue(hasattr(Message.objects, 'get_query_set'))

    def test_manager_has_get_queryset(self):
        self.assertTrue(hasattr(Message.objects, 'get_queryset'))


class UserPermissionTests(TestCase):

    def setUp(self):
        self.sender = User.objects.create(username='sender', email='sender@example.com')
        self.receiver1 = User.objects.create(username='receiver1', email='receiver1@example.com')
        self.receiver2 = User.objects.create(username='receiver2', email='receiver2@example.com')
        self.other = User.objects.create(username='other', email='other@example.com')

        self.group = CosinnusGroup.objects.create(name='group')
        self.othergroup = CosinnusGroup.objects.create(name='othergroup')

        for u in (self.sender, self.receiver1, self.receiver2):
            CosinnusGroupMembership.objects.create(user=u, group=self.group, status=MEMBERSHIP_MEMBER)

        CosinnusGroupMembership.objects.create(user=self.other, group=self.othergroup, status=MEMBERSHIP_MEMBER)

    def test_broadcast_private(self):
        m = _c(title='test_broadcast_public', creator=self.sender, group=self.group, isbroadcast=True, isprivate=True)
        m.recipients.add(self.receiver1)
        self.assertEqual(Message.objects.filter_for_user(self.sender).get(), m)
        self.assertEqual(Message.objects.filter_for_user(self.receiver1).get(), m)
        self.assertRaises(Message.DoesNotExist, Message.objects.filter_for_user(self.receiver2).get)
        self.assertRaises(Message.DoesNotExist, Message.objects.filter_for_user(self.other).get)
        self.assertRaises(Message.DoesNotExist, Message.objects.filter_for_user(None).get)

    def test_broadcast_notprivate(self):
        m = _c(title='test_broadcast_public', creator=self.sender, group=self.group, isbroadcast=True, isprivate=False)
        m.recipients.add(self.receiver1)
        self.assertEqual(Message.objects.filter_for_user(self.sender).get(), m)
        self.assertEqual(Message.objects.filter_for_user(self.receiver1).get(), m)
        self.assertEqual(Message.objects.filter_for_user(self.receiver2).get(), m)
        self.assertEqual(Message.objects.filter_for_user(self.other).get(), m)
        self.assertEqual(Message.objects.filter_for_user(None).get(), m)

    def test_notbroadcast_private(self):
        m = _c(title='test_broadcast_public', creator=self.sender, group=self.group, isbroadcast=False, isprivate=True)
        m.recipients.add(self.receiver1)
        self.assertEqual(Message.objects.filter_for_user(self.sender).get(), m)
        self.assertEqual(Message.objects.filter_for_user(self.receiver1).get(), m)
        self.assertRaises(Message.DoesNotExist, Message.objects.filter_for_user(self.receiver2).get)
        self.assertRaises(Message.DoesNotExist, Message.objects.filter_for_user(self.other).get)
        self.assertRaises(Message.DoesNotExist, Message.objects.filter_for_user(None).get)

    def test_notbroadcast_notprivate(self):
        m = _c(title='test_broadcast_public', creator=self.sender, group=self.group, isbroadcast=False, isprivate=False)
        m.recipients.add(self.receiver1)
        self.assertEqual(Message.objects.filter_for_user(self.sender).get(), m)
        self.assertEqual(Message.objects.filter_for_user(self.receiver1).get(), m)
        self.assertEqual(Message.objects.filter_for_user(self.receiver2).get(), m)
        self.assertEqual(Message.objects.filter_for_user(self.other).get(), m)
        self.assertEqual(Message.objects.filter_for_user(None).get(), m)
