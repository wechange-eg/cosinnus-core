# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import json
import six

from annoying.functions import get_object_or_None
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured, ValidationError, \
    PermissionDenied
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.encoding import force_text
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.views.generic import (CreateView, DeleteView, DetailView,
    ListView, UpdateView, TemplateView)

from cosinnus.conf import settings
from cosinnus.core import signals
from cosinnus.core.registries import app_registry
from cosinnus.core.registries.group_models import group_model_registry
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety, \
    ensure_group_type
from cosinnus.utils.urls import group_aware_reverse, get_non_cms_root_url


logger = logging.getLogger('cosinnus')



class UserDashboardView(TemplateView):
    
    template_name = 'cosinnus/user_dashboard/user_dashboard.html'
    
    def get_context_data(self, **kwargs):
        options = {
            
        }
        ctx = {
            'user_dashboard_options_json': json.dumps(options),
        }
        return ctx


user_dashboard_view = UserDashboardView.as_view()

