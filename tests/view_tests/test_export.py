# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from cosinnus.models import CosinnusGroup
from cosinnus.views.export import JSONExportView

from tests.models import ChoicesTestModel


class JSONExportViewTest(TestCase):

    def setUp(self):
        self.group = CosinnusGroup.objects.create(name='Group 1')

    def test_improperly_configured(self):
        """
        Should raise an AttributeError if model is not specified.
        """
        # assertRaises doesn't work when the exception is happening during
        # object's initialisation
        try:
            view = JSONExportView()
        except ImproperlyConfigured:
            pass
        else:
            self.fail()

    def test_get_data_no_fields(self):
        """
        Should retrieve a certain JSON string even if no fields specified
        """
        ChoicesTestModel.objects.create(group=self.group, title='title')
        class ExportView(JSONExportView):
            model = ChoicesTestModel
            group = self.group

        view = ExportView()
        data = view.get_data()
        self.assertIn('id', data['fields'])
        self.assertIn('title', data['fields'])
        self.assertIn(['1', 'title'], data['rows'])
        self.assertIn(self.group.name, data['group'])

    def test_get_data(self):
        """
        Should retrieve a certain JSON format with custom field specified
        """
        obj = ChoicesTestModel.objects.create(
            group=self.group,
            title='title1',
            state=ChoicesTestModel.STATE_SCHEDULED,
        )
        class ExportView(JSONExportView):
            model = ChoicesTestModel
            group = self.group
            fields = ['slug', 'state']
        view = ExportView()
        data = view.get_data()
        self.assertIn('slug', data['fields'])
        self.assertEqual(obj.get_state_display(), data['rows'][0][3])

    def test_get_data_two_rows(self):
        """
        Should have two rows if there are two objects of that group in database
        """
        ChoicesTestModel.objects.create(group=self.group, title='title1')
        ChoicesTestModel.objects.create(group=self.group, title='title2')
        group2 = CosinnusGroup.objects.create(name='Group 2')
        ChoicesTestModel.objects.create(group=group2, title='title2')
        class ExportView(JSONExportView):
            model = ChoicesTestModel
            group = self.group
        view = ExportView()
        data = view.get_data()
        self.assertEqual(len(ChoicesTestModel.objects.all()), 3)
        self.assertEqual(len(data['rows']), 2)

    def test_get(self):
        """
        Should have file prefix in response's content-disposition and content-type application/json
        """
        ChoicesTestModel.objects.create(group=self.group, title='title')
        class ExportView(JSONExportView):
            model = ChoicesTestModel
            group = self.group
            file_prefix = 'file_prefix'
        view = ExportView()
        response = view.get(self, None)
        self.assertIn('content-disposition', response)
        self.assertIn('filename="file_prefix', response['content-disposition'])
        self.assertIn('content-type', response)
        self.assertEqual('application/json', response['content-type'])
