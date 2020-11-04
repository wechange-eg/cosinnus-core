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
        from cosinnus.models.group_extra import ensure_group_type
        from cosinnus.utils.group import get_cosinnus_group_model
        obj = self
        # for groups make sure to update the correct CosinnusProject/CosinnusSociety index
        # instead of CosinnusGroup
        if type(obj) is get_cosinnus_group_model() or issubclass(obj.__class__, get_cosinnus_group_model()):
            obj = ensure_group_type(obj)
        obj.signal_processor.handle_save(obj.__class__, obj)
        
    def remove_index(self):
        """ Removes self from the proper search index depending on model """
        from cosinnus.models.group_extra import ensure_group_type
        from cosinnus.utils.group import get_cosinnus_group_model
        obj = self
        # for groups make sure to update the correct CosinnusProject/CosinnusSociety index
        # instead of CosinnusGroup
        if type(obj) is get_cosinnus_group_model() or issubclass(obj.__class__, get_cosinnus_group_model()):
            obj = ensure_group_type(obj)
        obj.signal_processor.handle_delete(obj.__class__, obj)
        
    
