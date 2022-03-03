# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from django.test import SimpleTestCase

from cosinnus.utils.http import JSONResponse


class JSONResponseTest(SimpleTestCase):

    content_type='application/json'

    def test_empty(self):
        r = JSONResponse({})
        self.assertEqual(r.content, b'{}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['content-type'], self.content_type)

    def test_number(self):
        r = JSONResponse({'num': 1})
        self.assertEqual(r.content, b'{"num": 1}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['content-type'], self.content_type)

    def test_float(self):
        r = JSONResponse({'float': 1.23})
        self.assertEqual(r.content, b'{"float": 1.23}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['content-type'], self.content_type)

    def test_datetime(self):
        r = JSONResponse({'datetime': datetime.datetime(2014, 3, 4, 12, 34, 56)})
        self.assertEqual(r.content, b'{"datetime": "2014-03-04T12:34:56"}')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['content-type'], self.content_type)

    def test_status_code(self):
        r = JSONResponse({'key': "val"}, status=404)
        self.assertEqual(r.content, b'{"key": "val"}')
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r['content-type'], self.content_type)
