# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from appconf import AppConf
from django.conf import settings  # noqa


class CosinnusMarketplaceConf(AppConf):
    class Meta(object):
        prefix = 'COSINNUS_MARKETPLACE'

    # default number of days offers in the Marketplace stay active
    OFFER_ACTIVITY_DURATION_DAYS = 180

    # if False, offers will expire after `COSINNUS_MARKETPLACE_OFFER_ACTIVITY_DURATION_DAYS`
    # (set to inactive by a cronjob)
    OFFER_EXPIRY_DISABLED = False
