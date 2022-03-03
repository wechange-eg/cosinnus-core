# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from django.forms import ValidationError

from cosinnus_todo.forms import TodoEntryForm
from cosinnus_todo.models import TodoEntry
from tests.form_tests.base import FormTestCase


class TodoEntryFormTest(FormTestCase):
    def test_fields(self):
        """
        Should have certain fields in form
        """
        fields = [
            # "normal" fields
            'title', 'due_date', 'assigned_to', 'completed_by',
            'completed_date', 'priority', 'note', 'tags'
            # no media_tag fields
        ]
        form = TodoEntryForm(group=self.group)
        self.assertEqual(fields, [k for k in list(form.fields.keys())])

    def test_init_assigned_to(self):
        """
        Should have querysets for assigned_to and completed_by set appropriately
        """
        form = TodoEntryForm(group=self.group)
        self.assertIn(self.admin, form.fields['assigned_to'].queryset)

    def test_init_completed_by(self):
        """
        Should have set assigned_to disabled if user is not allowed to
        assign
        """
        form = TodoEntryForm(group=self.group)
        self.assertIn(self.admin, form.fields['completed_by'].queryset)

    def test_init_assigned_to_other(self):
        """
        Should have set assigned_to disabled if other user is not allowed to
        assign
        """
        user = self.add_user('test')
        todo = TodoEntry.objects.create(
            group=self.group, title='testtodo', creator=self.admin)
        form = TodoEntryForm(group=self.group, user=user, instance=todo)
        self.assertEqual('disabled',
            form.fields['assigned_to'].widget.attrs['disabled'])

    def test_clean_assigned_to(self):
        user = self.add_user('test')
        todo = TodoEntry.objects.create(
            group=self.group, title='testtodo', creator=self.admin)

        # should barf when user is not allowed to assign
        form = TodoEntryForm(group=self.group, user=user, instance=todo)
        form.cleaned_data = {'assigned_to': user}
        self.assertRaises(ValidationError, form.clean_assigned_to)

        # should be fine when assigning as admin
        form = TodoEntryForm(group=self.group, user=self.admin, instance=todo)
        form.cleaned_data = {'assigned_to': user}
        self.assertEqual(form.clean_assigned_to(), user)

