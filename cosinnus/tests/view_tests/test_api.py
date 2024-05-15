# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.contrib.auth.models import User
from django.http import QueryDict
from django.test import Client, RequestFactory, SimpleTestCase, TestCase
from django.urls import reverse
from django.utils.encoding import force_str

from cosinnus.views.mixins.ajax import patch_body_json_data

"""
Note: These are tests for the legacy v1 API.
"""


class BaseApiTest(TestCase):
    def setUp(self):
        self.client = Client(HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.admin = User.objects.create_superuser('admin', 'admin@localhost', 'admin')

    def assertJsonEqual(self, response, obj):
        self.assertEqual(json.loads(force_str(response.content)), obj)

    def delete(self, name, *args, **kwargs):
        reverse_args = kwargs.pop('reverse_args', ())
        reverse_kwargs = kwargs.pop('reverse_kwargs', {})
        return self.client.delete(reverse(name, args=reverse_args, kwargs=reverse_kwargs), *args, **kwargs)

    def get(self, name, *args, **kwargs):
        reverse_args = kwargs.pop('reverse_args', ())
        reverse_kwargs = kwargs.pop('reverse_kwargs', {})
        return self.client.get(reverse(name, args=reverse_args, kwargs=reverse_kwargs), *args, **kwargs)

    def post(self, name, data, *args, **kwargs):
        reverse_args = kwargs.pop('reverse_args', ())
        reverse_kwargs = kwargs.pop('reverse_kwargs', {})
        return self.client.post(
            reverse(name, args=reverse_args, kwargs=reverse_kwargs),
            data=json.dumps(data),
            content_type='text/json; charset=UTF-8',
            *args,
            **kwargs,
        )

    def put(self, name, data, *args, **kwargs):
        reverse_args = kwargs.pop('reverse_args', ())
        reverse_kwargs = kwargs.pop('reverse_kwargs', {})
        return self.client.put(
            reverse(name, args=reverse_args, kwargs=reverse_kwargs),
            data=json.dumps(data),
            content_type='text/json; charset=UTF-8',
            *args,
            **kwargs,
        )


class HelperTest(SimpleTestCase):
    def test_patch_body_json_data(self):
        """
        Tests for null values being converted to an empty string in
        JSON POST data
        """
        factory = RequestFactory()
        data = {
            'string': 'Stringvalue',
            'int': 42,
            'float': 13.37,
            'none': None,
        }
        json_data = json.dumps(data)
        request = factory.post('/', data=json_data, content_type='text/json; charset=UTF-8')
        patch_body_json_data(request)
        query = QueryDict('string=Stringvalue&int=42&float=13.37&none')
        self.assertEqual(request._post, query)

    def test_patch_body_json_data_drop_dict(self):
        """
        Tests for dicts being removed if no ``'id'`` key exists
        """
        factory = RequestFactory()
        data = {
            'string': 'Stringvalue',
            'dict': {
                'some': 'value',
            },
        }
        json_data = json.dumps(data)
        request = factory.post('/', data=json_data, content_type='text/json; charset=UTF-8')
        patch_body_json_data(request)
        query = QueryDict('string=Stringvalue')
        self.assertEqual(request._post, query)

    def test_patch_body_json_data_replace_dict(self):
        """
        Tests for dicts being replaced by its ``'id'`` if present
        """
        factory = RequestFactory()
        data = {
            'string': 'Stringvalue',
            'dict': {
                'some': 'value',
                'id': 42,
            },
        }
        json_data = json.dumps(data)
        request = factory.post('/', data=json_data, content_type='text/json; charset=UTF-8')
        patch_body_json_data(request)
        query = QueryDict('string=Stringvalue&dict=42')
        self.assertEqual(request._post, query)
