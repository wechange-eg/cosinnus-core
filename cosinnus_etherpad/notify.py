# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.utils.urls import group_aware_reverse
from cosinnus_etherpad.models import Etherpad

NOTIFY_MODELS = [Etherpad]
NOTIFY_POST_SUBSCRIBE_URLS = {
    'etherpad.Etherpad': {
        'show': lambda obj, group: obj.get_absolute_url(),
        'list': lambda obj, group: group_aware_reverse('cosinnus:etherpad:list', kwargs={'group': group}),
    },
}
