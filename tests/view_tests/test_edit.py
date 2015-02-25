# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase

from cosinnus.models.group import CosinnusGroup
from cosinnus.models.tagged import get_tag_object_model
from cosinnus.utils.urls import group_aware_reverse


TagObject = get_tag_object_model()


class EditGroupTest(TestCase):

    def setUp(self, *args, **kwargs):
        self.group = CosinnusGroup.objects.create(name='Fäñæü ñáµé',
            slug='fancy-name', public=True)
        self.media_tag = TagObject.objects.create(group=self.group,
            location_place='Some Location', people_name='Somebody',
            public=True)
        self.credential = 'admin'
        self.admin = User.objects.create_superuser(
            username=self.credential, email=None, password=self.credential)
        self.client.login(username=self.credential, password=self.credential)
        self.url = group_aware_reverse('cosinnus:group-edit',
                           kwargs={'group': self.group})

    def test_get_not_logged_in(self):
        """
        Should return 403 on GET if not logged in
        """
        self.client.logout()  # default is logged-in
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_get_logged_in(self):
        """
        Should return 200 on GET when logged in
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_not_logged_in(self):
        """
        Should return 403 on POST if not logged in
        """
        self.client.logout()
        data = {
            'name': 'Fäñæü ñáµé',
            'slug': 'fancy-name',
        }
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 403)

    def test_post_logged_in(self):
        """
        Should return 302 to detail page on successful POST and have a todo
        with given title
        """
        data = {
            'name': 'Fäñæü ñáµé ²',
            'slug': 'fancy-name-2',
            'public': False,
            'media_tag-location_place': 'New Location',
            'media_tag-people_name': 'Anybody',
            'media_tag-public': False,
        }
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 302)

        group = CosinnusGroup.objects.select_related('media_tag').get(name=data['name'])
        self.assertEqual(group.name, data['name'])
        self.assertEqual(group.slug, data['slug'])
        self.assertEqual(group.public, data['public'])
        self.assertEqual(group.media_tag.location_place, data['media_tag-location_place'])
        self.assertEqual(group.media_tag.people_name, data['media_tag-people_name'])
        self.assertEqual(group.media_tag.public, data['media_tag-public'])
