# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.utils.renderer import BaseRenderer

class MessageRenderer(BaseRenderer):
    """
    MessageRenderer for Cosinnus attached objects
    
    Not needed, because messages can never be attached *to* anything, so set to empty.
    """
    model = None
    
    template = None
    template_single = None
    template_list = None
    
    @classmethod
    def render(cls, context, myobjs, **kwargs):
        return '' 
