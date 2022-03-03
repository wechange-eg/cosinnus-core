# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus_todo.forms import TodoEntryAssignForm
from tests.form_tests.base import FormTestCase


class TodoEntryAssignFormTest(FormTestCase):

    def test_fields(self):
        """
        Should have certain fields in form
        """
        fields = ['assigned_to']
        form = TodoEntryAssignForm(group=self.group)
        self.assertEqual(fields, [k for k in list(form.fields.keys())])
