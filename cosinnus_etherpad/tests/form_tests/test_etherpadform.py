# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
from django.test import TestCase
from uuid import uuid4

from cosinnus.models import CosinnusGroup
from cosinnus_etherpad.forms import EtherpadForm
from cosinnus_etherpad.models import Etherpad


class EtherpadFormTest(TestCase):

    def setUp(self):
        super(EtherpadFormTest, self).setUp()
        self.group = CosinnusGroup.objects.create(
            name='testgroup-' + str(uuid4()))
        title = 'testpad'
        self.pad = Etherpad.objects.create(
            group=self.group, title=title)
        self.data = {'title': title}

    def tearDown(self):
        # explicitly need to delete object, otherwise signals won't be fired
        # and pad/group on server will persist
        self.pad.delete()
        self.group.delete()
        super(EtherpadFormTest, self).tearDown()

    def test_readonly_title(self):
        """
        Should not set the title to readonly in the widget if instance is not
        given
        """
        form = EtherpadForm(group=self.group).forms['obj']
        self.assertNotIn('readonly', form.fields['title'].widget.attrs)

    def test_readonly_title_instance(self):
        """
        Should set the title to readonly in the widget if instance is given
        """
        form = EtherpadForm(group=self.group, instance=self.pad).forms['obj']
        self.assertTrue(form.fields['title'].widget.attrs['readonly'])

    def test_clean_title(self):
        """
        Should clean the title
        """
        form = EtherpadForm(group=self.group, data=self.data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.forms['obj'].clean_title(),
                         form.forms['obj'].cleaned_data['title'])

    def test_clean_title_instance(self):
        """
        Should clean the title with instance
        """
        form = EtherpadForm(group=self.group, data=self.data, instance=self.pad)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.forms['obj'].clean_title(), self.pad.title)
