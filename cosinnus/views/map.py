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
from django.http.response import HttpResponseNotAllowed, JsonResponse,\
    HttpResponseBadRequest, HttpResponse
from django.shortcuts import redirect
from cosinnus.templatetags.cosinnus_tags import full_name_force,\
    render_cosinnus_topics_field
from django.contrib.auth.views import password_reset, password_change
from cosinnus.utils.permissions import check_user_integrated_portal_member,\
    filter_tagged_object_queryset_for_user
from django.template.context import RequestContext
from django.template.response import TemplateResponse
from django.core.paginator import Paginator
from cosinnus.views.mixins.group import EndlessPaginationMixin
import json
from cosinnus.utils.user import filter_active_users
from django.conf import settings
from cosinnus.models.group_extra import CosinnusSociety, CosinnusProject
from django.contrib.staticfiles.templatetags.staticfiles import static
from cosinnus.utils.functions import is_number, ensure_list_of_ints
import six
from django.db.models import Q
from operator import __or__ as OR, __and__ as AND
from django.utils.encoding import force_text
from cosinnus.templatetags.cosinnus_map_tags import get_map_marker_icon_settings,\
    get_map_marker_icon_settings_json
from django.views.generic.base import TemplateView
from django.views.decorators.clickjacking import xframe_options_exempt
from django.forms.forms import BaseForm
from django.utils.html import escape
from cosinnus.views.map_api import get_searchresult_by_itemid


USER_MODEL = get_user_model()


class MapView(TemplateView):

    def get_context_data(self, **kwargs):
        ctx = {
            'markers': get_map_marker_icon_settings_json(),
            'skip_page_footer': True,
        }
        item = self.request.GET.get('item', None)
        if item:
            ctx.update({
                'item': get_searchresult_by_itemid(item)
            })
        return ctx

    template_name = 'cosinnus/map/map_page.html'

map_view = MapView.as_view()


class MapEmbedView(TemplateView):
    """ An embeddable, resizable Map view without any other elements than the map """
    
    template_name = 'cosinnus/universal/map/map_embed.html'
    
    @method_decorator(xframe_options_exempt)
    def dispatch(self, *args, **kwargs):
        return super(MapEmbedView, self).dispatch(*args, **kwargs)

map_embed_view = MapEmbedView.as_view()

