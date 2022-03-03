# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse

from cosinnus_event.models import Event


NOTIFY_MODELS = [Event]
NOTIFY_POST_SUBSCRIBE_URLS = {
    'event.Event': {
        'show': lambda obj, group: obj.get_absolute_url(),
        'list': lambda obj, group: reverse('sinn_event-entry-list', kwargs={'group': group.pk}),
    },
}
