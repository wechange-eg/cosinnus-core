# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse

from tests.view_tests.base import ViewTestCase


class AssignNoFieldTest(ViewTestCase):

    def test_assign_me(self):
        """
        Should assign todo entry to me
        """
        todo = self.execute_no_field('entry-assign-me')
        self.assertEqual(todo.assigned_to, self.admin)

    def _execute_invalid(self, urlname):
        credential = 'test'
        self.add_user(credential)
        self.client.login(username=credential, password=credential)
        url = reverse('cosinnus:todo:entry-' + urlname, kwargs=self.kwargs)
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, 200)

        kwargs = {'group': self.group.slug}
        list_url = reverse('cosinnus:todo:list', kwargs=kwargs)
        self.assertRedirects(response, list_url)

    def test_assign_me_other_user(self):
        """
        Should redirect to list page if other user tries to assign todo entry
        """
        self._execute_invalid('assign-me')

    def test_unassign_other_user(self):
        """
        Should redirect to list page if other user tries to unassign todo entry
        """
        self._execute_invalid('unassign')
