# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import timedelta
from django.test import TestCase
from django.utils.timezone import now

from cosinnus_todo.templatetags import todo_tags


class TodoTagsTest(TestCase):
    def test_is_past(self):
        dt = now()
        self.assertTrue(todo_tags.is_past(dt))

        dt = now() + timedelta(days=1)
        self.assertFalse(todo_tags.is_past(dt))
