# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from cosinnus.core.decorators.views import require_admin_access_decorator
from cosinnus.core.loaders.widgets import cosinnus_widget_registry as cwr
from cosinnus.models.widget import WidgetConfig
from cosinnus.utils.http import JSONResponse
from cosinnus.utils.permissions import check_ug_admin, check_ug_membership


def widget_list(request):
    data = {}
    for app, widgets in cwr:
        data[app] = tuple(widgets)
    return JSONResponse(data)


@login_required
def widget_add_user(request, app_name, widget_name):
    widget_class = cwr.get(app_name, widget_name)
    form_class = widget_class.get_setup_form_class()
    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            widget = widget_class.create(request, user=request.user)
            widget.save_config(form.cleaned_data)
            return JSONResponse({'id': widget.id})
    else:
        form = form_class()
    d = {'form': form}
    c = RequestContext(request)
    return render_to_response('cosinnus/widgets/setup.html', d, c)


@require_admin_access_decorator()
def widget_add_group(request, group, app_name, widget_name):
    widget_class = cwr.get(app_name, widget_name)
    form_class = widget_class.get_setup_form_class()
    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            widget = widget_class.create(request, group=group)
            widget.save_config(form.cleaned_data)
            return JSONResponse({'id': widget.id})
    else:
        form = form_class()
    d = {'form': form}
    c = RequestContext(request)
    return render_to_response('cosinnus/widgets/setup.html', d, c)


def widget_detail(request, id):
    wc = get_object_or_404(WidgetConfig, id=int(id))
    if wc.group and not check_ug_membership(request.user, wc.group) or \
            wc.user and wc.user_id != request.user.pk:
        return HttpResponseForbidden('Access denied!')
    widget_class = cwr.get(wc.app_name, wc.widget_name)
    widget = widget_class(request, wc)
    data = widget.get_data()
    if isinstance(data, six.string_types):
        return HttpResponse(data)
    return JSONResponse(data)


@csrf_exempt
@require_POST
def widget_delete(request, id):
    wc = get_object_or_404(WidgetConfig, id=int(id))
    if wc.group and not check_ug_admin(request.user, wc.group) or \
            wc.user and wc.user_id != request.user.pk:
        return HttpResponseForbidden('Access denied!')
    wc.delete()
    return HttpResponse('Widget removed')
