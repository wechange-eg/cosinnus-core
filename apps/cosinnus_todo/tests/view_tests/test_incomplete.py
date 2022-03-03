# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from tests.view_tests.base import ViewTestCase


class IncompleteTest(ViewTestCase):

    def test_incomplete(self):
        """
        Should mark todo entry incomplete
        """
        todo = self.execute_no_field('entry-incomplete')
        self.assertEqual(todo.completed_by, None)
        self.assertEqual(todo.completed_date, None)
