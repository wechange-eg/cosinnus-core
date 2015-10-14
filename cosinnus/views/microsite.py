# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.views.generic import TemplateView

from cosinnus.views.mixins.group import DipatchGroupURLMixin, GroupObjectCountMixin
from cosinnus.conf import settings
from django.http.response import Http404


class GroupMicrositeView(DipatchGroupURLMixin, GroupObjectCountMixin, TemplateView):
    template_name = 'cosinnus/group/group_microsite.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not getattr(settings, 'COSINNUS_MICROSITES_ENABLED', False):
            raise Http404
        return super(GroupMicrositeView, self).dispatch(request, *args, **kwargs)
    
group_microsite_view = GroupMicrositeView.as_view()
    
# this view is only called from within the group-startpage redirect view