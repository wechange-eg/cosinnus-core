# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.decorators import method_decorator
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView

from cosinnus.core.decorators.views import require_admin_access_decorator
from cosinnus.core.registries import widget_registry
from cosinnus.models.widget import WidgetConfig
from cosinnus.utils.http import JSONResponse
from cosinnus.utils.permissions import check_ug_admin, check_ug_membership
from cosinnus.views.mixins.group import RequireReadMixin


def widget_list(request):
    data = {}
    for app, widgets in widget_registry:
        data[app] = tuple(widgets)
    return JSONResponse(data)


@ensure_csrf_cookie
@login_required
def widget_add_user(request, app_name, widget_name):
    widget_class = widget_registry.get(app_name, widget_name)
    if widget_class is None:
        return render_to_response('cosinnus/widgets/not_found.html')
    if not widget_class.allow_on_user:
        return render_to_response('cosinnus/widgets/not_allowed_user.html')
    form_class = widget_class.get_setup_form_class()
    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            widget = widget_class.create(request, user=request.user)
            widget.save_config(form.cleaned_data)
            return JSONResponse({'id': widget.id})
    else:
        form = form_class()
    d = {
        'form': form,
        'submit_label': _('Add widget'),
    }
    c = RequestContext(request)
    return render_to_response('cosinnus/widgets/setup.html', d, c)


@ensure_csrf_cookie
@require_admin_access_decorator()
def widget_add_group(request, group, app_name, widget_name):
    widget_class = widget_registry.get(app_name, widget_name)
    if widget_class is None:
        return render_to_response('cosinnus/widgets/not_found.html')
    form_class = widget_class.get_setup_form_class()
    if not widget_class.allow_on_group:
        return render_to_response('cosinnus/widgets/not_allowed_group.html')
    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            widget = widget_class.create(request, group=group)
            widget.save_config(form.cleaned_data)
            return JSONResponse({'id': widget.id})
    else:
        form = form_class()
    d = {
        'form': form,
        'submit_label': _('Add widget'),
    }
    c = RequestContext(request)
    return render_to_response('cosinnus/widgets/setup.html', d, c)


@ensure_csrf_cookie
def widget_detail(request, id, offset=0):
    wc = get_object_or_404(WidgetConfig, id=int(id))
    if wc.group and not (check_ug_membership(request.user, wc.group) or
                         wc.group.public) or \
            wc.user and wc.user_id != request.user.pk:
        return HttpResponseForbidden('Access denied!')
    widget_class = widget_registry.get(wc.app_name, wc.widget_name)
    if widget_class is None:
        return render_to_response('cosinnus/widgets/not_found.html')
    widget = widget_class(request, wc)
    data, rows_returned, has_more = widget.get_data(int(offset))
    
    if isinstance(data, six.string_types):
        resp = HttpResponse(data)
    else:
        resp = JSONResponse(data)
    resp['X-Cosinnus-Widget-Title'] = force_text(widget.title)
    if widget.title_url is not None:
        resp['X-Cosinnus-Widget-Title-URL'] = force_text(widget.title_url)
    resp['X-Cosinnus-Widget-App-Name'] = force_text(wc.app_name)
    resp['X-Cosinnus-Widget-Widget-Name'] = force_text(wc.widget_name)
    resp['X-Cosinnus-Widget-Num-Rows-Returned'] = rows_returned
    resp['X-Cosinnus-Widget-Has-More-Data'] = 'true' if has_more else 'false'
    return resp


@ensure_csrf_cookie
def widget_delete(request, id):
    wc = get_object_or_404(WidgetConfig, id=int(id))
    if wc.group and not check_ug_admin(request.user, wc.group) or \
            wc.user and wc.user_id != request.user.pk:
        return HttpResponseForbidden('Access denied!')
    if request.method == "POST":
        wc.delete()
        return HttpResponse('Widget removed')
    else:
        c = RequestContext(request)
        return render_to_response('cosinnus/widgets/delete.html', {}, c)


@ensure_csrf_cookie
def widget_edit(request, id):
    wc = get_object_or_404(WidgetConfig, id=int(id))
    if wc.group and not check_ug_admin(request.user, wc.group) or \
            wc.user and wc.user_id != request.user.pk:
        return HttpResponseForbidden('Access denied!')
    widget_class = widget_registry.get(wc.app_name, wc.widget_name)
    if widget_class is None:
        return render_to_response('cosinnus/widgets/not_found.html')
    form_class = widget_class.get_setup_form_class()
    widget = widget_class(request, wc)
    if request.method == "POST":
        form = form_class(request.POST)
        if form.is_valid():
            widget.save_config(form.cleaned_data)
            return JSONResponse({'id': widget.id})
    else:
        form = form_class(initial=dict(widget.config))
    d = {
        'form': form,
        'submit_label': _('Change'),
    }
    c = RequestContext(request)
    return render_to_response('cosinnus/widgets/setup.html', d, c)


class DashboardMixin(object):
    template_name = 'cosinnus/dashboard.html'

    def get_context_data(self, **kwargs):
        filter = self.get_filter()
        widgets = WidgetConfig.objects.filter(**filter)
        ids = widgets.values_list('id', flat=True).all()
        kwargs.update({
            'widgets': ids,
        })
        
        """ We sort each unique widget into the context to be accessed hard-coded"""
        for wc in widgets:
            context_id = wc.app_name + '__' + wc.widget_name.replace(" ", "_")
            kwargs.update({context_id : wc.id})
        
        """ TODO: FIXME: Sascha """
        """ This code is a crime to humanity and was only added to have 
            this working for the beta really quickly. Refactor this into
            the note widget itself. (But don't put the Form through with 
            the ajax request in the widget loading algorithm! 
        """   
        # Only for the group dashboard:
        if hasattr(self, 'group'):  
            from cosinnus_note.forms import NoteForm
            kwargs.update({
                'form':  NoteForm(group=self.group)
            })
        
        return super(DashboardMixin, self).get_context_data(**kwargs)


class GroupDashboard(RequireReadMixin, DashboardMixin, TemplateView):

    def get_filter(self):
        return {'group_id': self.group.pk}

group_dashboard = GroupDashboard.as_view()


class UserDashboard(DashboardMixin, TemplateView):
    template_name = 'cosinnus/user_dashboard.html'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(UserDashboard, self).dispatch(request, *args, **kwargs)

    def get_filter(self):
        """ Submit the user id so queryset elements can be filtered for that user. """
        return {'user_id': self.request.user.pk}

user_dashboard = UserDashboard.as_view()
