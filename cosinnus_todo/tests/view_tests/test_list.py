# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import range, str

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.timezone import now

from cosinnus.models import CosinnusGroupMembership
from cosinnus.models.membership import MEMBERSHIP_MEMBER
from cosinnus_todo.models import TodoEntry, TodoList
from cosinnus_todo.tests.view_tests.base import ViewTestCase


class ListTest(ViewTestCase):
    def test_list_not_logged_in(self):
        """
        Should return 200 and contain URL to add a todo entry
        """
        kwargs = {'group': self.group.slug, 'listslug': 'general'}
        url = reverse('cosinnus:todo:list-list', kwargs=kwargs)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)

    def test_list_logged_in_admin(self):
        """
        Should return 200 and contain URL to add a todo entry
        """
        self.client.login(username=self.credential, password=self.credential)
        kwargs = {'group': self.group.slug, 'listslug': 'general'}
        url = reverse('cosinnus:todo:list-list', kwargs=kwargs)
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn(reverse('cosinnus:todo:entry-add', kwargs=kwargs), force_str(response.content))
