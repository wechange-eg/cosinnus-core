# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse

from cosinnus_marketplace.models import Offer


NOTIFY_MODELS = [Offer]
NOTIFY_POST_SUBSCRIBE_URLS = {
    'marketplace.Offer': {
        'show': lambda obj, group: obj.get_absolute_url(),
        'list': lambda obj, group: reverse('sinn_offer-entry-list', kwargs={'group': group.pk}),
    },
}
