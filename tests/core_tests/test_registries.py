# -*- coding: utf-8 -*-
from __future__ import unicode_literals


from django.conf.urls import patterns, url
from django.test import SimpleTestCase
from django.utils import unittest

from cosinnus.core.registries import (apps, attached_objects, base, urls,
    widgets)
from cosinnus.utils.compat import OrderedDict
from cosinnus.conf import settings


class TestBaseRegistry(SimpleTestCase):

    def setUp(self):
        self.reg = base.BaseRegistry()

    def test_not_implemented(self):
        self.assertRaises(NotImplementedError, self.reg.register,
            'Subclasses need to implement this method.')


class TestDictBaseRegistry(SimpleTestCase):

    def setUp(self):
        self.reg = base.DictBaseRegistry()

    def test_not_implemented(self):
        self.assertRaises(NotImplementedError, self.reg.register,
            'Subclasses need to implement this method.')

    def test_init(self):
        self.assertIsInstance(self.reg._storage, OrderedDict)
        self.assertEqual(self.reg._storage, {})

    def test_item_access(self):
        def getitem_keyerror(key):
            return self.reg[key]
        def del_keyerror(key):
            del self.reg[key]
        self.reg['foo'] = 'bar'
        self.assertTrue('foo' in self.reg)
        self.assertEqual(self.reg._storage, {'foo': 'bar'})
        self.assertEqual(self.reg['foo'], 'bar')
        self.reg._storage['lorem'] = 'ipsum'
        self.assertFalse('ipsum' in self.reg)
        self.assertEqual(self.reg.get('lorem'), 'ipsum')
        self.assertIsNone(self.reg.get('nokey'))
        self.assertEqual(self.reg.get('nokey', 'something'), 'something')
        self.assertRaises(KeyError, getitem_keyerror, 'nokey')
        self.assertRaises(KeyError, del_keyerror, 'nokey')
        self.assertEqual(tuple((k, self.reg[k]) for k in self.reg),
            (('foo', 'bar', ), ('lorem', 'ipsum'),))
        self.reg.unregister('foo')
        self.assertIsNone(self.reg.get('foo'))
        self.reg.unregister('nokey')


class TestAppRegistry(SimpleTestCase):

    def setUp(self):
        self.reg = apps.AppRegistry()

    def test_register(self):
        self.reg.register('full.path.to.app', 'app_name', 'app_label')
        self.assertEqual(self.reg.get_name('full.path.to.app'), 'app_name')
        self.assertEqual(self.reg.get_label('full.path.to.app'), 'app_label')

    def test_register_empty_label(self):
        self.reg.register('full.path.to.app', 'app_name')
        self.assertEqual(self.reg.get_name('full.path.to.app'), 'app_name')
        self.assertEqual(self.reg.get_label('full.path.to.app'), 'App_Name')

    def test_register_invalid_app_name(self):
        self.assertRaises(AttributeError, self.reg.register, 'app', 'Foo#bar')
        self.assertFalse('app' in self.reg)

    def test_items(self):
        apps = (
            ('some.app1', 'name1', 'Label 1'),
            ('some.app2', 'name2', 'Label 2'),
            ('some.app3', 'name3', 'Label 3'),
        )
        for app in apps:
            self.reg.register(*app)
        self.assertEqual(tuple(self.reg.items()), apps)

    def test_items_reverse(self):
        apps = (
            ('some.app1', 'name1', 'Label 1'),
            ('some.app2', 'name2', 'Label 2'),
            ('some.app3', 'name3', 'Label 3'),
        )
        for app in reversed(apps):
            self.reg.register(*app)
        self.assertEqual(tuple(self.reg.items()), tuple(reversed(apps)))


class TestAttachedObjectRegistry(SimpleTestCase):

    def setUp(self):
        self.reg = attached_objects.AttachedObjectRegistry()

    @unittest.skip("Not implemented yet")
    def test_register(self):
        raise NotImplementedError()


class TestURLRegistry(SimpleTestCase):

    @classmethod
    def setUpClass(cls):
        def _view(request, *args, **kwargs):
            return request, args, kwargs

        cls.view_func = _view
        cls.root_patterns = patterns('',
            url(r'^root/view/$', cls.view_func, name='root-view'),
        )
        cls.group_patterns = patterns('',
            url(r'^%s/view/$' % settings.COSINNUS_GROUP_URL_PATH, cls.view_func, name='group-view'),
        )

    def setUp(self):
        self.reg = urls.URLRegistry()
        apps.app_registry.register('some_app', 'some_name', 'some_label')

    def tearDown(self):
        apps.app_registry.unregister('some_app')

    def test_register(self):
        self.reg.register('some_app', self.root_patterns, self.group_patterns)
        root_url, group_url = self.reg.urlpatterns

        self.assertEqual(root_url.app_name, 'some_app')
        self.assertEqual(root_url.namespace, 'some_name')
        self.assertEqual(root_url.regex.pattern, '')
        self.assertEqual(root_url.url_patterns[0].callback, TestURLRegistry.view_func)
        self.assertEqual(root_url.url_patterns[0].name, 'root-view')
        self.assertEqual(root_url.url_patterns[0].regex.pattern, '^root/view/$')

        self.assertEqual(group_url.app_name, 'some_app')
        self.assertEqual(group_url.namespace, 'some_name')
        self.assertEqual(group_url.regex.pattern, '^%s/(?P<group>[^/]+)/some_name/' % settings.COSINNUS_GROUP_URL_PATH)
        self.assertEqual(group_url.url_patterns[0].callback, TestURLRegistry.view_func)
        self.assertEqual(group_url.url_patterns[0].name, 'group-view')
        self.assertEqual(group_url.url_patterns[0].regex.pattern, '^%s/view/$' % settings.COSINNUS_GROUP_URL_PATH)


class TestWidgetRegistry(SimpleTestCase):

    def setUp(self):
        self.reg = widgets.WidgetRegistry()

    @unittest.skip("Not implemented yet")
    def test_register(self):
        raise NotImplementedError()
