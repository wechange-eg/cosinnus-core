# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.utils.urls import group_aware_reverse
from cosinnus_file.models import FileEntry

NOTIFY_MODELS = [FileEntry]
NOTIFY_POST_SUBSCRIBE_URLS = {
    'file.FileEntry': {
        'show': lambda obj, group: obj.get_absolute_url(),
        'list': lambda obj, group: group_aware_reverse('cosinnus:file:list', kwargs={'group': group}),
    },
}
