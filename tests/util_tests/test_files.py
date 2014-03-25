# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.test import SimpleTestCase

from cosinnus.utils.files import get_avatar_filename


class AvatarTest(SimpleTestCase):

    def test_get_avatar_filename(self):

        class Profile(object):
            user_id = 1337

        profile = Profile()
        filename = 'avatar.png'

        filepath = get_avatar_filename(profile, filename)
        expected = 'cosinnus/avatars/users/37d49d9d9ed8afa7d555512c4bf59bc92c8b3c41.png'

        self.assertEqual(filepath, expected)
