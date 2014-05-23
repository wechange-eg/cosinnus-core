# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.templatetags.cosinnus_tags import full_name


def get_user_choices(users):
    for user in users:
        yield (user.id, full_name(user))
