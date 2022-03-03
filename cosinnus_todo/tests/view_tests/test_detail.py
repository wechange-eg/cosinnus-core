# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse
from django.utils.encoding import force_text

from cosinnus_todo.models import TodoEntry
from tests.view_tests.base import ViewTestCase


class DetailTest(ViewTestCase):

    def test_detail(self):
        """
        Should return 200 and contain todo title
        """
        todo = TodoEntry.objects.create(
            group=self.group, title='testtitle', creator=self.admin)
        kwargs = {'group': self.group.slug, 'slug': todo.slug}
        url = reverse('cosinnus:todo:entry-detail', kwargs=kwargs)
        response = self.client.get(url)

        # should return 200
        self.assertEqual(response.status_code, 200)

        # content should contain pad title
        self.assertIn(todo.title, force_text(response.content))
