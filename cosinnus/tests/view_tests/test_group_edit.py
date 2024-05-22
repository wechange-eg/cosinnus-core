# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.test import TestCase

from cosinnus.models.group import CosinnusGroup
from cosinnus.models.tagged import get_tag_object_model
from cosinnus.utils.urls import group_aware_reverse

TagObject = get_tag_object_model()


class EditGroupTest(TestCase):
    def setUp(self, *args, **kwargs):
        self.group = CosinnusGroup.objects.create(name='Fäñæü ñáµé', slug='fancy-name', public=True)
        self.media_tag = TagObject.objects.create(group=self.group, location='Some Location', public=True)
        self.credential = 'admin'
        self.admin = User.objects.create_superuser(
            username=self.credential, email='admin@example.com', password=self.credential
        )
        self.client.login(username=self.credential, password=self.credential)
        self.url = group_aware_reverse('cosinnus:group-edit', kwargs={'group': self.group})

    def test_get_not_logged_in(self):
        """
        Should return redirect to login GET if not logged in
        """
        self.client.logout()  # default is logged-in
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_get_logged_in(self):
        """
        Should return 200 on GET when logged in
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_not_logged_in(self):
        """
        Should return redirect to group page on POST if not logged in
        """
        self.client.logout()
        data = {
            'name': 'Fäñæü ñáµé',
        }
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 302)
        self.assertIn('?next=', response['Location'])

    def test_post_logged_in(self):
        """
        Should return 302 to detail page on successful POST and have a todo
        with given title
        """
        data = {
            'name': 'Fäñæü ñáµé ²',
            'slug': 'fancy-name-2',
            'public': False,
            'video_conference_type': CosinnusGroup.NO_VIDEO_CONFERENCE,
            'media_tag-location': 'New Location',
            'locations-TOTAL_FORMS': 0,
            'locations-INITIAL_FORMS': 0,
            'gallery_images-TOTAL_FORMS': 0,
            'gallery_images-INITIAL_FORMS': 0,
            'call_to_action_buttons-TOTAL_FORMS': 0,
            'call_to_action_buttons-INITIAL_FORMS': 0,
        }
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 302)

        group = CosinnusGroup.objects.select_related('media_tag').get(name=data['name'])
        self.assertEqual(group.name, data['name'])
        self.assertEqual(group.public, data['public'])
        self.assertEqual(group.media_tag.location, data['media_tag-location'])
