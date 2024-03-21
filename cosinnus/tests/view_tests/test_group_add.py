# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import User
from django.urls import reverse
from django.test import TestCase

from cosinnus.models.group import CosinnusGroup


class AddGroupTest(TestCase):

    def setUp(self, *args, **kwargs):
        self.credential = 'admin'
        self.admin = User.objects.create_superuser(
            username=self.credential, email='admin@example.com', password=self.credential
        )
        self.admin.cosinnus_profile.email_verified = True
        self.admin.cosinnus_profile.save()
        self.client.login(username=self.credential, password=self.credential)
        self.url = reverse('cosinnus:group-add')

    def test_get_not_logged_in(self):
        """
        Should return 403 on GET if not logged in
        """
        self.client.logout()  # default is logged-in
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('next=' + self.url, response['Location'])

    def test_get_logged_in(self):
        """
        Should return 200 on GET when logged in
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_not_logged_in(self):
        """
        Should redirect to login on POST if not logged in
        """
        self.client.logout()
        data = {
            'name': 'Fäñæü ñáµé',
            'slug': 'fancy-name',
        }
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, 302)
        self.assertIn('next=' + self.url, response['Location'])

    def test_post_logged_in(self):
        """
        Should return 302 to detail page on successful POST and have a todo
        with given title
        """
        data = {
            'name': 'Fäñæü ñáµé',
            'slug': 'faenue-nae',
            'public': True,
            'video_conference_type': CosinnusGroup.NO_VIDEO_CONFERENCE,
            'media_tag-location': 'Location',
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
        self.assertEqual(group.slug, data['slug'])
        self.assertEqual(group.public, data['public'])
        self.assertEqual(group.media_tag.location, data['media_tag-location'])
