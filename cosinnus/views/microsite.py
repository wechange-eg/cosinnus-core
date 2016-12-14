# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict

from django.contrib.auth.models import AnonymousUser
from django.http.response import Http404
from django.views.generic import TemplateView

from cosinnus.conf import settings
from cosinnus.views.mixins.group import DipatchGroupURLMixin, GroupObjectCountMixin
from cosinnus.views.mixins.tagged import DisplayTaggedObjectsMixin


class GroupMicrositeView(DipatchGroupURLMixin, GroupObjectCountMixin, DisplayTaggedObjectsMixin, TemplateView):
    template_name = 'cosinnus/group/group_microsite.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not getattr(settings, 'COSINNUS_MICROSITES_ENABLED', False):
            raise Http404
        return super(GroupMicrositeView, self).dispatch(request, *args, **kwargs)
    
    def get_public_objects(self):
        """ Returns a dict {'<app_name': [<app_items>], ...} """
        querysets = self.get_object_querysets(group=self.group, cosinnus_apps=self.group.get_microsite_public_apps())
        
        public_objects = defaultdict(list)
        for queryset in querysets:
            items = self.sort_and_limit_single_queryset(queryset, item_limit=settings.COSINNUS_MICROSITE_PUBLIC_APPS_NUMBER_OF_ITEMS)
            if items:
                public_objects[items[0].get_cosinnus_app_name()].extend(items)
        
        return dict(public_objects)#.items()
    
    def get_context_data(self, **kwargs):
        context = super(GroupMicrositeView, self).get_context_data(**kwargs)
        context.update({
            'public_objects': self.get_public_objects(),
            'anonymous_user': AnonymousUser(),
        })
        return context
    
group_microsite_view = GroupMicrositeView.as_view()
    
# this view is only called from within the group-startpage redirect view
