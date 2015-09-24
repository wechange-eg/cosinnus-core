# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView

from cosinnus.views.mixins.group import RequireWriteMixin, DipatchGroupURLMixin
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


class GroupMicrositeView(DipatchGroupURLMixin, TemplateView):
    template_name = 'cosinnus/group/group_microsite.html'
    
    
    
# this view is only called from within the group-startpage redirect view