# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView

from cosinnus.views.mixins.group import RequireWriteMixin
from cosinnus.models.widget import WidgetConfig
from cosinnus.conf import settings
from cosinnus.models.group import CosinnusGroup
from django.http.response import HttpResponseNotFound
from cosinnus.models.cms import CosinnusMicropage
from cosinnus.core.registries import widget_registry
from cosinnus.core.decorators.views import redirect_to_403,\
    get_group_for_request
from cosinnus.utils.permissions import check_object_write_access
from cosinnus.core.registries.attached_objects import attached_object_registry
from cosinnus.utils.functions import get_cosinnus_app_from_class
from cosinnus.views.widget import DashboardWidgetMixin


class GroupMicrosite(DashboardWidgetMixin, TemplateView):
    """ TODO: Refactor-merge and unify this view to a mixin with DashboardMixin for groups,
        after this view has been generalized to allow Organisations instead of Groups.
    """
    template_name = 'cosinnus/microsite.html'
    group_url_kwarg = 'group'
    
    
    def dispatch(self, request, *args, **kwargs):
        group_name = kwargs.get(self.group_url_kwarg, None)
        group = get_group_for_request(group_name, request)
        self.group = group
        return super(GroupMicrosite, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        
        """ Item list inline views """
        item_inlines = []
        item_limit = 5
        for model_name in settings.COSINNUS_MICROSITE_DISPLAYED_APP_OBJECTS:
            Renderer = attached_object_registry.get(model_name)
            if Renderer:
                qs_filter = {'group__slug': self.group.slug}
                app_name = get_cosinnus_app_from_class(Renderer)
                content = Renderer.render_list_for_user(self.request.user, self.request, 
                                qs_filter, limit=item_limit, 
                                render_if_empty=settings.COSINNUS_MICROSITE_RENDER_EMPTY_APPS, 
                                standalone_app=app_name)
                if content:
                    item_inlines.append({
                        'model': model_name,
                        'app_name': app_name,
                        'content': content,
                    })
        
        kwargs.update({
            'group': self.group,
            'edit_mode': False,
            'item_inlines': item_inlines,
        })
        return super(GroupMicrosite, self).get_context_data(**kwargs)

    def get_filter(self):
        return {'group_id': self.group.pk, 'type': WidgetConfig.TYPE_MICROSITE}
    
group_microsite = GroupMicrosite.as_view()

        
class GroupMicrositeEdit(GroupMicrosite, RequireWriteMixin):
    
    def dispatch(self, request, *args, **kwargs):
        """ Assure write access to group """
        group_name = kwargs.get(self.group_url_kwarg, None)
        group = get_group_for_request(group_name, request)
        self.group = group
        if (check_object_write_access(self.group, request.user)):
            return super(GroupMicrosite, self).dispatch(request, *args, **kwargs)
        # Access denied, redirect to 403 page and and display an error message
        return redirect_to_403(request)
            
    def get_context_data(self, **kwargs):
        context = super(GroupMicrositeEdit, self).get_context_data(**kwargs)
        context.update({
            'edit_mode':True
        })
        return context
    
group_microsite_edit = GroupMicrositeEdit.as_view()
