# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django_cron import CronJobBase, Schedule

from cosinnus.conf import settings
from datetime import timedelta
from cosinnus_marketplace.models import Offer
from cosinnus.models.group import CosinnusPortal
from django.utils.timezone import now
from cosinnus.cron import CosinnusCronJobBase


class DeactivateExpiredOffers(CosinnusCronJobBase):
    
    RUN_EVERY_MINS = 60 # every 1 hour
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    
    cosinnus_code = 'marketplace.deactivate_expired_offers'
    
    def do(self):
        if getattr(settings, 'COSINNUS_MARKETPLACE_OFFER_EXPIRY_DISABLED', False):
            return
        
        expiry_days = getattr(settings, 'COSINNUS_MARKETPLACE_OFFER_ACTIVITY_DURATION_DAYS', 30)
        expired_offers = Offer.objects.filter(group__portal=CosinnusPortal.get_current(),
              is_active=True, created__lte=(now() - timedelta(days=expiry_days)))
        
        for offer in expired_offers:
            offer.do_expire_this()
            
        return "Expired offers: %d" % len(expired_offers)
    