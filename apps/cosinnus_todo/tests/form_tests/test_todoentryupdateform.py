# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.utils.test import get_fieldnames_from_multiform

from cosinnus_todo.forms import TodoEntryUpdateForm

from tests.form_tests.base import FormTestCase


class TodoEntryUpdateFormTest(FormTestCase):

    def test_fields(self):
        """
        Should have certain fields in form
        """
        fields = {
            # "normal" fields
            'obj': [
                'title', 'due_date', 'new_list', 'todolist', 'assigned_to',
                'completed_by', 'completed_date', 'priority', 'note', 'tags',
            ],
            # media_tag fields
            'media_tag': [
                'location_place', 'people_name', 'public'
            ]
        }
        form = TodoEntryUpdateForm(group=self.group)
        real = get_fieldnames_from_multiform(form)
        self.assertEqual(fields, real)

    def test_init(self):
        """
        Should have querysets for assigned_to and completed_by set appropriately
        """
        form = TodoEntryUpdateForm(group=self.group).forms['obj']
        self.assertIn(self.admin, form.fields['assigned_to'].queryset)
