# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict

from django.contrib.auth.models import AnonymousUser
from django.http.response import Http404
from django.views.generic import TemplateView

from cosinnus.conf import settings
from cosinnus.views.mixins.group import DipatchGroupURLMixin, GroupObjectCountMixin
from cosinnus.views.mixins.tagged import DisplayTaggedObjectsMixin
from cosinnus.core.decorators.views import redirect_to_not_logged_in
from billiard.five import items


class GroupMicrositeView(DipatchGroupURLMixin, GroupObjectCountMixin, DisplayTaggedObjectsMixin, TemplateView):
    
    def dispatch(self, request, *args, **kwargs):
        if not getattr(settings, 'COSINNUS_MICROSITES_ENABLED', False):
            raise Http404
        # if microsite access is limited, only allow invite-links, but nothing else
        if not self.request.user.is_authenticated and getattr(settings, 'COSINNUS_MICROSITES_DISABLE_ANONYMOUS_ACCESS', False) \
                and not request.GET.get('invited', None) == '1':
            return redirect_to_not_logged_in(self.request, view=self)
        return super(GroupMicrositeView, self).dispatch(request, *args, **kwargs)
    
    def get_template_names(self):
        """ Return the extending compact-conference microsite if this is a conference
            and conferences are shown in compact mode """
        if self.group.group_is_conference:
            return ['cosinnus/group/conference_compact_microsite.html']
        return ['cosinnus/group/group_microsite.html']
    
    def get_public_objects(self):
        """ Returns a list of tuples [('<app>', <app_name>'m [<app_items>]), ...] """
        querysets = self.get_object_querysets(group=self.group, cosinnus_apps=self.group.get_microsite_public_apps())
        
        public_object_list = defaultdict(list)
        for queryset in querysets:
            items = self.sort_and_limit_single_queryset(queryset, item_limit=settings.COSINNUS_MICROSITE_PUBLIC_APPS_NUMBER_OF_ITEMS)
            if items:
                public_object_list[items[0].get_cosinnus_app_name()].extend(items)
        public_objects = []
        for app_name, items in public_object_list.items():
            public_objects.append((items[0].get_cosinnus_app(), app_name, items))
        return public_objects
    
    def get_context_data(self, **kwargs):
        context = super(GroupMicrositeView, self).get_context_data(**kwargs)
        context.update({
            'public_objects': self.get_public_objects(),
            'anonymous_user': AnonymousUser(),
        })
        return context
    
group_microsite_view = GroupMicrositeView.as_view()
    
# this view is only called from within the group-startpage redirect view
