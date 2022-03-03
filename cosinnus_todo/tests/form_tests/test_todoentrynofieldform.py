# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus_todo.forms import TodoEntryNoFieldForm
from tests.form_tests.base import FormTestCase


class TodoEntryNoFieldFormTest(FormTestCase):

    def test_fields(self):
        """
        Should have certain fields in form
        """
        form = TodoEntryNoFieldForm(group=self.group)
        self.assertEqual([], [k for k in list(form.fields.keys())])
