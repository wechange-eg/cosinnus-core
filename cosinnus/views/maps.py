# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model, login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.urlresolvers import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from cosinnus.core.decorators.views import staff_required, superuser_required,\
    redirect_to_not_logged_in, redirect_to_403
from cosinnus.forms.user import UserCreationForm, UserChangeForm
from cosinnus.views.mixins.ajax import patch_body_json_data
from cosinnus.utils.http import JSONResponse
from django.contrib import messages
from cosinnus.models.profile import get_user_profile_model
from cosinnus.models.tagged import BaseTagObject
from cosinnus.models.group import CosinnusPortal
from cosinnus.core.mail import MailThread, get_common_mail_context,\
    send_mail_or_fail_threaded
from django.template.loader import render_to_string
from django.http.response import HttpResponseNotAllowed
from django.shortcuts import redirect
from cosinnus.templatetags.cosinnus_tags import full_name_force
from django.contrib.auth.views import password_reset, password_change
from cosinnus.utils.permissions import check_user_integrated_portal_member
from django.template.context import RequestContext
from django.template.response import TemplateResponse
from django.core.paginator import Paginator
from cosinnus.views.mixins.group import EndlessPaginationMixin


USER_MODEL = get_user_model()


class MapView(ListView):

    model = USER_MODEL
    template_name = 'cosinnus/map/map.html'
    

map_view = MapView.as_view()
