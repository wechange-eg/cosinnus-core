# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import TestCase

from cosinnus.models.tagged import CosinnusGroup

from tests.models import SlugTestModel


class SlugTest(TestCase):

    def setUp(self):
        self.group = CosinnusGroup.objects.create(name='Group 1')

    def test_new_slug(self):
        m1 = SlugTestModel.objects.create(group=self.group, title='Some Title')
        self.assertEqual(m1.slug, 'some-title')
        m2 = SlugTestModel.objects.create(group=self.group, title='Some Title')
        self.assertEqual(m2.slug, 'some-title-2')

    def test_existing_slug(self):
        m = SlugTestModel.objects.create(group=self.group, title='Some Title')
        self.assertEqual(m.slug, 'some-title')
        m.title = 'Other title'
        m.save()
        self.assertEqual(m.slug, 'some-title')
        m.title = 'Yet another title'
        m.save(update_fields=['title'])
        self.assertEqual(m.slug, 'some-title')
        m.title = 'Yet another title 2'
        m.save(update_fields=('title', 'slug'))
        self.assertEqual(m.slug, 'some-title')

    def test_long_title(self):
        key = 'abcdefghij'
        title = key * 25 + 'abcde'
        m1 = SlugTestModel.objects.create(group=self.group, title=title)
        self.assertEqual(m1.slug, key * 5)
        m2 = SlugTestModel.objects.create(group=self.group, title=title)
        self.assertEqual(m2.slug, key * 5 + '-2')
