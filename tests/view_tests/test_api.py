# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase, Client
from django.utils.encoding import force_text

from cosinnus.models import (CosinnusGroup, CosinnusGroupMembership,
    MEMBERSHIP_ADMIN, MEMBERSHIP_MEMBER, MEMBERSHIP_PENDING)


class BaseApiTest(TestCase):

    def setUp(self):
        self.client = Client(HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.admin = User.objects.create_superuser('admin', 'admin@localhost', 'admin')

    def assertJsonEqual(self, response, obj):
        self.assertEqual(json.loads(force_text(response.content)), obj)


class GroupTest(BaseApiTest):

    def test_group_list_empty(self):
        resp = self.client.get(reverse('cosinnus-api:group-list'))
        self.assertJsonEqual(resp, [])

    def test_group_list_filled(self):
        g1 = CosinnusGroup.objects.create(name='Group 1', public=True)
        g2 = CosinnusGroup.objects.create(name='Group 2', public=True)
        CosinnusGroup.objects.create(name='Group 3', public=False)
        resp = self.client.get(reverse('cosinnus-api:group-list'))
        self.assertJsonEqual(resp, [{
            'id': g1.id,
            'name': g1.name,
            'slug': g1.slug,
            'public': g1.public,
        }, {
            'id': g2.id,
            'name': g2.name,
            'slug': g2.slug,
            'public': g2.public,
        }])

    def test_group_list_filled_private_group(self):
        g1 = CosinnusGroup.objects.create(name='Group 1', public=True)
        g2 = CosinnusGroup.objects.create(name='Group 2', public=True)
        g3 = CosinnusGroup.objects.create(name='Group 3', public=False)
        self.client.login(username='admin', password='admin')
        resp = self.client.get(reverse('cosinnus-api:group-list'))
        self.assertJsonEqual(resp, [{
            'id': g1.id,
            'name': g1.name,
            'slug': g1.slug,
            'public': g1.public,
        }, {
            'id': g2.id,
            'name': g2.name,
            'slug': g2.slug,
            'public': g2.public,
        }, {
            'id': g3.id,
            'name': g3.name,
            'slug': g3.slug,
            'public': g3.public,
        }])

    def test_group_detail_no_existing(self):
        resp = self.client.get(reverse('cosinnus-api:group-detail',
                                       kwargs={'group': 'i-dont-exist'}))
        self.assertEqual(force_text(resp.content), 'No group found with this name')

    def test_group_detail_public(self):
        g = CosinnusGroup.objects.create(name='Group', public=True)
        resp = self.client.get(reverse('cosinnus-api:group-detail',
                                       kwargs={'group': g.slug}))
        self.assertJsonEqual(resp, {
            'id': g.id,
            'name': g.name,
            'slug': g.slug,
            'public': g.public,
        })

    def test_group_detail_private_no_access(self):
        g = CosinnusGroup.objects.create(name='Group', public=False)
        resp = self.client.get(reverse('cosinnus-api:group-detail',
                                       kwargs={'group': g.slug}))
        self.assertEqual(force_text(resp.content), 'Access denied')

    def test_group_detail_public_private(self):
        g = CosinnusGroup.objects.create(name='Group', public=True)
        self.client.login(username='admin', password='admin')
        resp = self.client.get(reverse('cosinnus-api:group-detail',
                                       kwargs={'group': g.slug}))
        self.assertJsonEqual(resp, {
            'id': g.id,
            'name': g.name,
            'slug': g.slug,
            'public': g.public,
        })


class GroupUsersTest(BaseApiTest):

    def setUp(self):
        super(GroupUsersTest, self).setUp()
        self.group = CosinnusGroup.objects.create(name='Group', public=True)

    def test_group_list_empty(self):
        resp = self.client.get(reverse('cosinnus-api:group-user-list',
                                       kwargs={'group': self.group.slug}))
        self.assertJsonEqual(resp, [])

    def test_group_list_filled(self):
        u1 = User.objects.create_user('user1')
        u2 = User.objects.create_user('user2')
        u3 = User.objects.create_user('user3')
        User.objects.create_user('user4')
        CosinnusGroupMembership.objects.create(user=u1, group=self.group, status=MEMBERSHIP_ADMIN)
        CosinnusGroupMembership.objects.create(user=u2, group=self.group, status=MEMBERSHIP_MEMBER)
        CosinnusGroupMembership.objects.create(user=u3, group=self.group, status=MEMBERSHIP_PENDING)
        resp = self.client.get(reverse('cosinnus-api:group-user-list',
                                       kwargs={'group': self.group.slug}))
        self.assertJsonEqual(resp, [{
            'id': u1.id,
            'username': u1.username,
        }, {
            'id': u2.id,
            'username': u2.username,
        }, {
            'id': u3.id,
            'username': u3.username,
        }])
