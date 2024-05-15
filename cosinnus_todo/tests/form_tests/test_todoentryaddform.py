# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.utils.test import get_fieldnames_from_multiform
from cosinnus_todo.forms import TodoEntryAddForm
from cosinnus_todo.tests.form_tests.base import FormTestCase


class TodoEntryAddFormTest(FormTestCase):
    def test_fields(self):
        """
        Should have certain fields in form
        """
        fields = {
            # "normal" fields
            'obj': ['title', 'note', 'due_date', 'new_list', 'todolist', 'assigned_to', 'priority', 'attached_objects'],
            # media_tag fields
            'media_tag': [
                'persons',
                'tags',
                'visibility',
                'public',
                'location',
                'location_lat',
                'location_lon',
                'place',
                'valid_start',
                'valid_end',
                'approach',
                'topics',
                'text_topics',
                'bbb_room',
                'like',
            ],
        }
        form = TodoEntryAddForm(group=self.group)
        real = get_fieldnames_from_multiform(form)
        self.assertEqual(fields, real)

    def test_init(self):
        """
        Should have querysets for assigned_to and completed_by set appropriately
        """
        form = TodoEntryAddForm(group=self.group).forms['obj']
        self.assertIn(self.admin, form.fields['assigned_to'].queryset)
