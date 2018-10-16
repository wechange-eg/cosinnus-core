# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
import logging
from haystack.signals import BaseSignalProcessor
from haystack import connection_router, connections

logger = logging.getLogger('cosinnus')


class IndexingUtilsMixin(object):
    """ Adds update/remove index util functions to a model """
    
    signal_processor = BaseSignalProcessor(connections, connection_router)
    
    def update_index(self):
        """ Updates self in the proper search index depending on model """
        self.signal_processor.handle_save(self.__class__, self)
        
    def remove_index(self):
        """ Removes self from the proper search index depending on model """
        self.signal_processor.handle_delete(self.__class__, self)
        
    
