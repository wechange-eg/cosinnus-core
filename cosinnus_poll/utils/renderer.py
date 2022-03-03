# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.utils.renderer import BaseRenderer
from cosinnus_poll.models import Poll


class PollRenderer(BaseRenderer):
    """
    PollRenderer for Cosinnus attached objects
    """
    model = Poll
    
    template = 'cosinnus_poll/attached_polls.html'
    template_v2 = 'cosinnus_poll/v2/attached_polls.html'
    template_single = 'cosinnus_poll/single_poll.html'
    template_list = 'cosinnus_poll/poll_list_standalone.html'
    
    @classmethod
    def render(cls, context, myobjs, **kwargs):
        return super(PollRenderer, cls).render(context, polls=myobjs, **kwargs)
