# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from django.test import TestCase
from unittest.mock import patch

from cosinnus.utils.files import get_avatar_filename


class AvatarTest(TestCase):

    @patch('cosinnus.utils.files.uuid4', return_value='492cf1cf-0dbd-4855-ad43-ca228ce4b022')
    def test_get_avatar_filename(self, user_uuid):

        class Profile(object):
            user_id = 1337

        profile = Profile()
        filename = 'avatar.png'



        filepath = get_avatar_filename(profile, filename)

        expected_file_hash = '81cbdd49c5835cbaa2fb26b8a56d7ffaae5796a1'
        expected = f'cosinnus_portals/portal_default/avatars/user/{expected_file_hash}.png'

        self.assertEqual(filepath, expected)
