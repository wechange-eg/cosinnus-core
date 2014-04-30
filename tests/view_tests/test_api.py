# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
import json

from os import path, unlink

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import QueryDict
from django.test import Client, SimpleTestCase, TestCase, RequestFactory
from django.utils.encoding import force_text

from cosinnus.models.group import (CosinnusGroup, CosinnusGroupMembership,
    MEMBERSHIP_ADMIN, MEMBERSHIP_MEMBER, MEMBERSHIP_PENDING)

from cosinnus.views.mixins.ajax import patch_body_json_data

from tests.utils import skipIfCustomUserProfileSerializer, skipUnlessCustomUserProfileSerializer


class BaseApiTest(TestCase):

    def setUp(self):
        self.client = Client(HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.admin = User.objects.create_superuser('admin', 'admin@localhost', 'admin')

    def assertJsonEqual(self, response, obj):
        self.assertEqual(json.loads(force_text(response.content)), obj)

    def delete(self, name, *args, **kwargs):
        reverse_args = kwargs.pop('reverse_args', ())
        reverse_kwargs = kwargs.pop('reverse_kwargs', {})
        return self.client.delete(reverse(name, args=reverse_args, kwargs=reverse_kwargs),
            *args, **kwargs)

    def get(self, name, *args, **kwargs):
        reverse_args = kwargs.pop('reverse_args', ())
        reverse_kwargs = kwargs.pop('reverse_kwargs', {})
        return self.client.get(reverse(name, args=reverse_args, kwargs=reverse_kwargs),
            *args, **kwargs)

    def post(self, name, data, *args, **kwargs):
        reverse_args = kwargs.pop('reverse_args', ())
        reverse_kwargs = kwargs.pop('reverse_kwargs', {})
        return self.client.post(reverse(name, args=reverse_args, kwargs=reverse_kwargs),
            data=json.dumps(data), content_type='text/json; charset=UTF-8',
            *args, **kwargs)

    def put(self, name, data, *args, **kwargs):
        reverse_args = kwargs.pop('reverse_args', ())
        reverse_kwargs = kwargs.pop('reverse_kwargs', {})
        return self.client.put(reverse(name, args=reverse_args, kwargs=reverse_kwargs),
            data=json.dumps(data), content_type='text/json; charset=UTF-8',
            *args, **kwargs)


class HelperTest(SimpleTestCase):

    def test_patch_body_json_data(self):
        """
        Tests for null values being converted to an empty string in
        JSON POST data
        """
        factory = RequestFactory()
        data = {
            'string': 'Stringvalue',
            'int': 42,
            'float': 13.37,
            'none': None,
        }
        json_data = json.dumps(data)
        request = factory.post('/', data=json_data,
            content_type='text/json; charset=UTF-8')
        patch_body_json_data(request)
        query = QueryDict('string=Stringvalue&int=42&float=13.37&none')
        self.assertEqual(request._post, query)

    def test_patch_body_json_data_drop_dict(self):
        """
        Tests for dicts being removed if no ``'id'`` key exists
        """
        factory = RequestFactory()
        data = {
            'string': 'Stringvalue',
            'dict': {
                'some': 'value',
            }
        }
        json_data = json.dumps(data)
        request = factory.post('/', data=json_data,
            content_type='text/json; charset=UTF-8')
        patch_body_json_data(request)
        query = QueryDict('string=Stringvalue')
        self.assertEqual(request._post, query)

    def test_patch_body_json_data_replace_dict(self):
        """
        Tests for dicts being replaced by its ``'id'`` if present
        """
        factory = RequestFactory()
        data = {
            'string': 'Stringvalue',
            'dict': {
                'some': 'value',
                'id': 42,
            }
        }
        json_data = json.dumps(data)
        request = factory.post('/', data=json_data,
            content_type='text/json; charset=UTF-8')
        patch_body_json_data(request)
        query = QueryDict('string=Stringvalue&dict=42')
        self.assertEqual(request._post, query)


class AuthTest(BaseApiTest):

    def test_login_success(self):
        User.objects.create_user('user', password='pass')
        resp = self.post('cosinnus-api:login', {
            'username': 'user',
            'password': 'pass',
        })
        self.assertEqual(resp.status_code, 200)

    def test_login_wrong_input(self):
        self.maxDiff = None
        User.objects.create_user('user', password='pass')
        resp = self.post('cosinnus-api:login', {
            'username': 'nobody',
            'password': 'wrong',
        })
        self.assertEqual(resp.status_code, 401)
        self.assertJsonEqual(resp, {
            '__all__': ['Please enter a correct username and password. Note '
                        'that both fields may be case-sensitive.']
        })

    def test_login_invalid_method(self):
        self.maxDiff = None
        User.objects.create_user('user', password='pass')
        resp = self.get('cosinnus-api:login')
        self.assertEqual(resp.status_code, 405)

    def test_logout(self):
        self.maxDiff = None
        u = User.objects.create_user('user', password='pass')
        self.client.login(username='user', password='pass')
        self.assertIn('_auth_user_id', self.client.session)
        self.assertEqual(self.client.session['_auth_user_id'], u.pk)
        resp = self.get('cosinnus-api:logout')
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)


class GroupTest(BaseApiTest):

    def test_group_list_empty(self):
        """
        Tests for an empty list returned if no groups exist
        """
        resp = self.get('cosinnus-api:group-list')
        self.assertJsonEqual(resp, [])

    def test_group_list_filled(self):
        """
        Tests that anonymous can only see public groups
        """
        g1 = CosinnusGroup.objects.create(name='Group 1', public=True)
        g2 = CosinnusGroup.objects.create(name='Group 2', public=True)
        CosinnusGroup.objects.create(name='Group 3', public=False)
        resp = self.get('cosinnus-api:group-list')
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
        """
        Tests that a group member of a private group can see that group
        """
        g1 = CosinnusGroup.objects.create(name='Group 1', public=True)
        g2 = CosinnusGroup.objects.create(name='Group 2', public=True)
        g3 = CosinnusGroup.objects.create(name='Group 3', public=False)
        u = User.objects.create_user('user', password='user')
        CosinnusGroupMembership.objects.create(user=u, group=g3, status=MEMBERSHIP_MEMBER)
        self.client.login(username='user', password='user')
        resp = self.get('cosinnus-api:group-list')
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
        """
        Tests that a request to a none-existing group returns a 404
        """
        resp = self.get('cosinnus-api:group-detail',
                        reverse_kwargs={'group': 'i-dont-exist'})
        self.assertEqual(force_text(resp.content), 'No group found with this name')
        self.assertEqual(resp.status_code, 404)

    def test_group_detail_public(self):
        """
        Tests that a group detail view returns the data about a public group
        """
        g = CosinnusGroup.objects.create(name='Group', public=True)
        resp = self.get('cosinnus-api:group-detail',
                        reverse_kwargs={'group': g.slug})
        self.assertJsonEqual(resp, {
            'id': g.id,
            'name': g.name,
            'slug': g.slug,
            'public': g.public,
        })

    def test_group_detail_private_not_logged_in(self):
        """
        Tests that a group detail view returns no data about a private group if
        not logged in
        """
        g = CosinnusGroup.objects.create(name='Group', public=False)
        resp = self.get('cosinnus-api:group-detail',
                        reverse_kwargs={'group': g.slug})
        self.assertEqual(force_text(resp.content), 'Access denied')
        self.assertEqual(resp.status_code, 403)

    def test_group_detail_private_logged_in(self):
        """
        Tests that a group detail view returns data about a private group if
        logged in
        """
        g = CosinnusGroup.objects.create(name='Group', public=False)
        u = User.objects.create_user('user', password='user')
        CosinnusGroupMembership.objects.create(user=u, group=g, status=MEMBERSHIP_MEMBER)
        self.client.login(username='user', password='user')
        resp = self.get('cosinnus-api:group-detail',
                        reverse_kwargs={'group': g.slug})
        self.assertJsonEqual(resp, {
            'id': g.id,
            'name': g.name,
            'slug': g.slug,
            'public': g.public,
        })

    def test_group_create(self):
        """
        Tests creation of a new group and auto slug
        """
        self.assertEqual(CosinnusGroup.objects.all().count(), 0)
        self.client.login(username='admin', password='admin')
        resp = self.post('cosinnus-api:group-add', data={
            'name': 'Some Group',
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(CosinnusGroup.objects.all().count(), 1)
        g = CosinnusGroup.objects.all().get()
        self.assertEqual(g.name, 'Some Group')
        self.assertEqual(g.slug, 'some-group')
        self.assertEqual(g.public, False)

    def test_group_create_all_fields(self):
        """
        Tests creation of a new group with all fields given
        """
        self.assertEqual(CosinnusGroup.objects.all().count(), 0)
        self.client.login(username='admin', password='admin')
        resp = self.post('cosinnus-api:group-add', data={
            'name': 'Some Group',
            'slug': 'something-else',
            'public': True,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(CosinnusGroup.objects.all().count(), 1)
        g = CosinnusGroup.objects.all().get()
        self.assertEqual(g.name, 'Some Group')
        self.assertEqual(g.slug, 'something-else')
        self.assertEqual(g.public, True)

    def test_group_delete(self):
        """
        Tests deletion of a group w/o members
        """
        g = CosinnusGroup.objects.create(name='Group', public=False)
        self.assertEqual(CosinnusGroup.objects.all().count(), 1)
        self.client.login(username='admin', password='admin')
        resp = self.delete('cosinnus-api:group-delete',
                           reverse_kwargs={'group': g.slug})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(CosinnusGroup.objects.all().count(), 0)

    def test_group_delete_with_users(self):
        """
        Tests deletion of a group w/ members
        """
        g = CosinnusGroup.objects.create(name='Group', public=False)
        u1 = User.objects.create_user('user1')
        u2 = User.objects.create_user('user2')
        CosinnusGroupMembership.objects.create(user=u1, group=g, status=MEMBERSHIP_MEMBER)
        CosinnusGroupMembership.objects.create(user=u2, group=g, status=MEMBERSHIP_MEMBER)

        self.assertEqual(CosinnusGroup.objects.all().count(), 1)
        self.assertEqual(CosinnusGroupMembership.objects.all().count(), 2)
        self.client.login(username='admin', password='admin')
        resp = self.delete('cosinnus-api:group-delete',
                           reverse_kwargs={'group': g.slug})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(CosinnusGroup.objects.all().count(), 0)
        self.assertEqual(CosinnusGroupMembership.objects.all().count(), 0)

    def test_group_update(self):
        """
        Tests update of a group
        """
        g = CosinnusGroup.objects.create(name='Group', slug='group', public=False)
        self.assertEqual(CosinnusGroup.objects.all().count(), 1)
        self.client.login(username='admin', password='admin')
        resp = self.put('cosinnus-api:group-edit',
                        reverse_kwargs={'group': g.slug},
                        data={
                            'name': 'Group 2',
                            'slug': 'group-2',
                            'public': True,
                        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(CosinnusGroup.objects.all().count(), 1)
        g = CosinnusGroup.objects.all().get()
        self.assertEqual(g.name, 'Group 2')
        self.assertEqual(g.slug, 'group-2')
        self.assertEqual(g.public, True)


class GroupUsersTest(BaseApiTest):

    def setUp(self):
        super(GroupUsersTest, self).setUp()
        self.group = CosinnusGroup.objects.create(name='Group', public=True)

    def tearDown(self):
        base = path.join('tests', 'util_tests', 'avatar.png')
        for fn in ['.80x80_q85_crop.png', '.50x50_q85_crop.png', '.40x40_q85_crop.png']:
            name = base + fn
            if path.exists(name):
                unlink(name)

    def test_group_list_empty(self):
        """
        Tests for an empty list returned if group has no users
        """
        resp = self.get('cosinnus-api:group-user-list',
                        reverse_kwargs={'group': self.group.slug})
        self.assertJsonEqual(resp, [])

    @skipIfCustomUserProfileSerializer
    def test_group_list_filled(self):
        """
        Tests that anonymous can all users assigned to a group (pending,
        member, admin)
        """
        u1 = User.objects.create_user('user1')
        u2 = User.objects.create_user('user2')
        u3 = User.objects.create_user('user3')
        User.objects.create_user('user4')
        CosinnusGroupMembership.objects.create(user=u1, group=self.group, status=MEMBERSHIP_ADMIN)
        CosinnusGroupMembership.objects.create(user=u2, group=self.group, status=MEMBERSHIP_MEMBER)
        CosinnusGroupMembership.objects.create(user=u3, group=self.group, status=MEMBERSHIP_PENDING)
        u2.cosinnus_profile.avatar = path.join('tests', 'util_tests', 'avatar.png')
        u2.cosinnus_profile.save()
        resp = self.get('cosinnus-api:group-user-list',
                        reverse_kwargs={'group': self.group.slug})
        self.assertJsonEqual(resp, [{
            'id': u1.id,
            'username': u1.username,
            'profile': {
                'id': u1.cosinnus_profile.id,
                'avatar': None,
                "avatar_80x80": None,
                "avatar_50x50": None,
                "avatar_40x40": None,
            },
        }, {
            'id': u2.id,
            'username': u2.username,
            'profile': {
                'id': u2.cosinnus_profile.id,
                "avatar": "/media/tests/util_tests/avatar.png",
                "avatar_80x80": "/media/tests/util_tests/avatar.png.80x80_q85_crop.png",
                "avatar_50x50": "/media/tests/util_tests/avatar.png.50x50_q85_crop.png",
                "avatar_40x40": "/media/tests/util_tests/avatar.png.40x40_q85_crop.png",
            },
        }, {
            'id': u3.id,
            'username': u3.username,
            'profile': {
                'id': u3.cosinnus_profile.id,
                'avatar': None,
                "avatar_80x80": None,
                "avatar_50x50": None,
                "avatar_40x40": None,
            },
        }])

    @skipUnlessCustomUserProfileSerializer
    def test_group_list_filled_custom(self):
        """
        Tests that anonymous can all users assigned to a group (pending,
        member, admin)
        """
        u1 = User.objects.create_user('user1')
        u2 = User.objects.create_user('user2')
        u3 = User.objects.create_user('user3')
        User.objects.create_user('user4')
        CosinnusGroupMembership.objects.create(user=u1, group=self.group, status=MEMBERSHIP_ADMIN)
        CosinnusGroupMembership.objects.create(user=u2, group=self.group, status=MEMBERSHIP_MEMBER)
        CosinnusGroupMembership.objects.create(user=u3, group=self.group, status=MEMBERSHIP_PENDING)
        u2.cosinnus_profile.dob = datetime.date(2014, 4, 25)
        u2.cosinnus_profile.save()
        resp = self.get('cosinnus-api:group-user-list',
                        reverse_kwargs={'group': self.group.slug})
        self.assertJsonEqual(resp, [{
            'id': u1.id,
            'username': u1.username,
            'profile': {
                'id': u1.cosinnus_profile.id,
                'dob': None,
            },
        }, {
            'id': u2.id,
            'username': u2.username,
            'profile': {
                'id': u2.cosinnus_profile.id,
                'dob': '2014-04-25',
            },
        }, {
            'id': u3.id,
            'username': u3.username,
            'profile': {
                'id': u3.cosinnus_profile.id,
                'dob': None,
            },
        }])
