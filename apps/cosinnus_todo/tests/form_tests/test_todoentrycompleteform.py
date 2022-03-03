# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus_todo.forms import TodoEntryCompleteForm
from tests.form_tests.base import FormTestCase


class TodoEntryCompleteFormTest(FormTestCase):

    def test_fields(self):
        """
        Should have certain fields in form
        """
        fields = ['completed_by', 'completed_date']
        form = TodoEntryCompleteForm(group=self.group)
        self.assertEqual(fields, [k for k in list(form.fields.keys())])
