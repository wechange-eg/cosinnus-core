# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
import logging
import haystack

logger = logging.getLogger('cosinnus')


class IndexingUtilsMixin(object):
    """ Adds update/remove index util functions to a model """
    
    def update_index(self):
        """ Updates self in the proper search index depending on model """
        haystack.signal_processor.handle_save(self.__class__, self)
        
    def remove_index(self):
        """ Removes self from the proper search index depending on model """
        haystack.signal_processor.handle_delete(self.__class__, self)
        
    
