# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.utils.renderer import BaseRenderer
from cosinnus_event.models import Event


class EventRenderer(BaseRenderer):
    """
    EventRenderer for Cosinnus attached objects
    """
    model = Event
    
    template = 'cosinnus_event/attached_events.html'
    template_v2 = 'cosinnus_event/v2/attached_events.html'
    template_single = 'cosinnus_event/single_event.html'
    template_list = 'cosinnus_event/event_list_standalone.html'
    
    @classmethod
    def render(cls, context, myobjs, **kwargs):
        return super(EventRenderer, cls).render(context, events=myobjs, **kwargs)
