# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os

from builtins import object
from django.test import TestCase

from cosinnus.utils.files import get_avatar_filename


class AvatarTest(TestCase):

    def test_get_avatar_filename(self):

        class Profile(object):
            user_id = 1337

        profile = Profile()
        filename = 'avatar.png'

        avatar_filepath = get_avatar_filename(profile, filename)
        avatar_path, avatar_file = os.path.split(avatar_filepath)

        self.assertEqual('cosinnus_portals/portal_default/avatars/user', avatar_path)

        expected_filename_hash_length = 44
        self.assertEqual(len(avatar_file), expected_filename_hash_length)
        self.assertNotIn(filename, avatar_file)
