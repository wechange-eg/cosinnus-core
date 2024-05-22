# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse

from cosinnus_poll.models import Poll

NOTIFY_MODELS = [Poll]
NOTIFY_POST_SUBSCRIBE_URLS = {
    'poll.Poll': {
        'show': lambda obj, group: obj.get_absolute_url(),
        'list': lambda obj, group: reverse('sinn_poll-entry-list', kwargs={'group': group.pk}),
    },
}
