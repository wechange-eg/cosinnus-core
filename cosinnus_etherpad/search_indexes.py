
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from haystack import indexes

from cosinnus.utils.search import BaseHierarchicalTaggableObjectIndex

from cosinnus_etherpad.models import Etherpad, Ethercalc


class EtherpadIndex(BaseHierarchicalTaggableObjectIndex, indexes.Indexable):

    def get_model(self):
        return Etherpad
    
    
class EthercalcIndex(BaseHierarchicalTaggableObjectIndex, indexes.Indexable):

    def get_model(self):
        return Ethercalc
