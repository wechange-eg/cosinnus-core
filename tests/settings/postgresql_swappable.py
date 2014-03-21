# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from tests.settings.postgresql import *


INSTALLED_APPS = INSTALLED_APPS + (
    'tests.swappable_models',
)

COSINNUS_USER_PROFILE_MODEL='cosinnus_test_swappable.CustomUserProfile'
