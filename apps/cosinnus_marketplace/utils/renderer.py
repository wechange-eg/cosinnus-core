# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.utils.renderer import BaseRenderer
from cosinnus_marketplace.models import Offer


class OfferRenderer(BaseRenderer):
    """
    OfferRenderer for Cosinnus attached objects
    """
    model = Offer
    
    template = 'cosinnus_marketplace/attached_offers.html'
    template_v2 = 'cosinnus_marketplace/v2/attached_offers.html'
    template_single = 'cosinnus_marketplace/single_offer.html'
    template_list = 'cosinnus_marketplace/offer_list_standalone.html'
    
    @classmethod
    def render(cls, context, myobjs, **kwargs):
        return super(OfferRenderer, cls).render(context, offers=myobjs, **kwargs)
