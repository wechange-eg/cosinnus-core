# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from haystack import indexes

from cosinnus.utils.search import BaseTaggableObjectIndex

from cosinnus_marketplace.models import Offer


class OfferIndex(BaseTaggableObjectIndex, indexes.Indexable):

    def get_model(self):
        return Offer
    
    def index_queryset(self, *args, **kwargs):
        """ Only include active offers """
        qs = super(OfferIndex, self).index_queryset(*args, **kwargs)
        qs = qs.filter(is_active=True)
        return qs
