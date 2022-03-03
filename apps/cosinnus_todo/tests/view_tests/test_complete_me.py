# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from tests.view_tests.base import ViewTestCase


class CompleteMeTest(ViewTestCase):

    def test_complete_me(self):
        """
        Should complete todo entry by me
        """
        todo = self.execute_no_field('entry-complete-me')
        self.assertEqual(todo.completed_by, self.admin)
        self.assertNotEqual(todo.completed_date, None)
