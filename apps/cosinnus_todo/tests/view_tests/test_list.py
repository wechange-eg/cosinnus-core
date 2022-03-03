# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
from builtins import range
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.encoding import force_text
from django.utils.timezone import now

from cosinnus.models import CosinnusGroupMembership
from cosinnus.models.membership import MEMBERSHIP_MEMBER

from cosinnus_todo.models import TodoEntry
from tests.view_tests.base import ViewTestCase


class ListTest(ViewTestCase):

    def test_list_not_logged_in(self):
        """
        Should return 200 and contain URL to add a todo entry
        """
        kwargs = {'group': self.group.slug}
        url = reverse('cosinnus:todo:list', kwargs=kwargs)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)


    def test_list_logged_in_admin(self):
        """
        Should return 200 and contain URL to add a todo entry
        """
        self.client.login(username=self.credential, password=self.credential)
        kwargs = {'group': self.group.slug}
        url = reverse('cosinnus:todo:list', kwargs=kwargs)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            reverse('cosinnus:todo:entry-add', kwargs=kwargs),
            force_text(response.content))

    def test_filtered_invalid_tag(self):
        """
        Should return 404 on invalid tag
        """
        kwargs = {'group': self.group.slug, 'tag': 'foo'}
        url = reverse('cosinnus:todo:list-filtered', kwargs=kwargs)

        # should return 404
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_filtered_valid_tag(self):
        """
        Should return 200 on valid tag and URL to edit todo entry
        """
        tag = 'foo'
        todo = TodoEntry.objects.create(
            group=self.group, title='testtodo', creator=self.admin)
        todo.tags.add(tag)
        kwargs = {'group': self.group.slug, 'tag': tag}
        url = reverse('cosinnus:todo:list-filtered', kwargs=kwargs)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        kwargs = {'group': self.group.slug, 'slug': todo.slug}
        self.assertIn(
            reverse('cosinnus:todo:entry-detail', kwargs=kwargs),
            str(response.content))  # type byte in Python3.3

    def test_max_queries_unassigned_uncompleted(self):
        tags = tuple('t%d' % i for i in range(1, 16))
        user = User.objects.create_user(username='user', password='user')
        CosinnusGroupMembership.objects.create(user=user, group=self.group,
            status=MEMBERSHIP_MEMBER)
        for i in range(1, 11):
            t = TodoEntry.objects.create(group=self.group, title='Todo%d' % i,
                creator=self.admin)
            t.tags.add(*tags[i-1:5])

        url = reverse('cosinnus:todo:list', kwargs={'group': self.group.slug})
        self.client.login(username='user', password='user')
        with self.assertNumQueries(9):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_max_queries_assigned_uncompleted(self):
        tags = tuple('t%d' % i for i in range(1, 16))
        user = User.objects.create_user(username='user', password='user')
        CosinnusGroupMembership.objects.create(user=user, group=self.group,
            status=MEMBERSHIP_MEMBER)
        for i in range(1, 11):
            t = TodoEntry.objects.create(group=self.group, title='Todo%d' % i,
                creator=self.admin, assigned_to=user)
            t.tags.add(*tags[i-1:5])

        url = reverse('cosinnus:todo:list', kwargs={'group': self.group.slug})
        self.client.login(username='user', password='user')
        with self.assertNumQueries(9):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_max_queries_unassigned_completed(self):
        tags = tuple('t%d' % i for i in range(1, 16))
        user = User.objects.create_user(username='user', password='user')
        CosinnusGroupMembership.objects.create(user=user, group=self.group,
            status=MEMBERSHIP_MEMBER)
        for i in range(1, 11):
            t = TodoEntry.objects.create(group=self.group, title='Todo%d' % i,
                creator=self.admin, completed_by=user, completed_date=now())
            t.tags.add(*tags[i-1:5])

        url = reverse('cosinnus:todo:list', kwargs={'group': self.group.slug})
        self.client.login(username='user', password='user')
        with self.assertNumQueries(9):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)

    def test_max_queries_assigned_completed(self):
        tags = tuple('t%d' % i for i in range(1, 16))
        user = User.objects.create_user(username='user', password='user')
        CosinnusGroupMembership.objects.create(user=user, group=self.group,
            status=MEMBERSHIP_MEMBER)
        for i in range(1, 11):
            t = TodoEntry.objects.create(group=self.group, title='Todo%d' % i,
                creator=self.admin, assigned_to=user, completed_by=user,
                completed_date=now())
            t.tags.add(*tags[i-1:5])

        url = reverse('cosinnus:todo:list', kwargs={'group': self.group.slug})
        self.client.login(username='user', password='user')
        with self.assertNumQueries(9):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
