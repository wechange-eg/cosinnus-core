# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render_to_response, render
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
from django.template.loader import render_to_string
from django.core.exceptions import ImproperlyConfigured
from uuid import uuid1


def widget_list(request):
    data = {}
    for app, widgets in widget_registry:
        data[app] = tuple(widgets)
    return JSONResponse(data)


def widget_add_user(request, app_name, widget_name):
    return widget_add_group(request, None, app_name, widget_name)


@ensure_csrf_cookie
@require_admin_access_decorator()
def widget_add_group(request, group, app_name=None, widget_name=None):
    template_name = 'cosinnus/widgets/add_widget.html'
    extra_context = {'form_view': 'add'}
    
    if request.method == "POST":
        print ">>> request arrived"
        widget_class = widget_registry.get(app_name, widget_name)
        if widget_class is None:
            return render_to_response('cosinnus/widgets/not_found.html')
        form_class = widget_class.get_setup_form_class()
        if not widget_class.allow_on_group:
            return render_to_response('cosinnus/widgets/not_allowed_group.html')
        
        form = form_class(request.POST, group=group)
        if form.is_valid():
            # the onl difference to user seems to be:
            if not group:
                widget = widget_class.create(request, user=request.user)
            else:
                widget = widget_class.create(request, group=group)
            widget.save_config(form.cleaned_data)
            
            return HttpResponse(widget.render(user=request.user, request=request, group=group))
        raise Exception("Form was invalid for widget add: ", app_name, widget_name, form_class)
    else:
        data = []
        for app_name, widgets in widget_registry:
            form_active = True
            for widget_name in widgets:
                widget_class = widget_registry.get(app_name, widget_name)
                if widget_class is None:
                    print ">>>>widg not found:", app_name, widget_name
                    continue
                form_class = widget_class.get_setup_form_class()
                if not getattr(form_class, "template_name", None):
                    #raise ImproperlyConfigured('Widget form "%s %s" has no attribute "template_name" configured!' % (app_name, widget_name))
                    print '>> ignoring widget "%s %s" without template_name form: ' %  (app_name, widget_name)
                    continue
                context = {'form': form_class(group=group)}
                print ">> widg trying to:", app_name, widget_name, widget_class, form_class, form_class.template_name
                widget_form_content = render(request, form_class.template_name, context).content
                data.append({
                    'app_name': app_name,
                    'widget_name': widget_name,
                    'form_content': widget_form_content,
                    'form_id': '%s_%s_%d' % (app_name, widget_name, uuid1()),
                    'form_active': form_active,
                })
                form_active = False #only first form is active
        context = {'widget_data': data}
        context.update(extra_context)
        
        return render(request, template_name, context)


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
def widget_edit(request, id, app_name=None, widget_name=None):
    template_name = 'cosinnus/widgets/add_widget.html'
    extra_context = {'form_view': 'edit'}
    
    wc = get_object_or_404(WidgetConfig, id=int(id))
    if wc.group and not check_ug_admin(request.user, wc.group) or \
            wc.user and wc.user_id != request.user.pk:
        return HttpResponseForbidden('Access denied!')
    
    if app_name and widget_name and (wc.app_name != app_name or wc.widget_name != widget_name):
        print ">>>>> THIS WIDGET WAS SET UP TO BE SWAPPED BY EDITING IT!"
        print ">> TODO: create new widget using create function, transfer important values, then delete this widget! "
        import ipdb; ipdb.set_trace();
    
    widget_class = widget_registry.get(wc.app_name, wc.widget_name)
    if widget_class is None:
        return render_to_response('cosinnus/widgets/not_found.html')
    form_class = widget_class.get_setup_form_class()
    widget = widget_class(request, wc)
    
    if request.method == "POST":
        form = form_class(request.POST, group=wc.group)
        if form.is_valid():
            widget.save_config(form.cleaned_data)
            return HttpResponse(widget.render(user=request.user, request=request, group=wc.group))
        
        raise Exception("Form was invalid for widget edit: ", app_name, widget_name, form_class)
    else:
        data = []
        for app_name, widgets in widget_registry:
            for widget_name in widgets:
                form_active = False
                
                widget_class = widget_registry.get(app_name, widget_name)
                if widget_class is None:
                    print ">>>>widg not found:", app_name, widget_name
                    continue
                form_class = widget_class.get_setup_form_class()
                if not getattr(form_class, "template_name", None):
                    #raise ImproperlyConfigured('Widget form "%s %s" has no attribute "template_name" configured!' % (app_name, widget_name))
                    print '>> ignoring widget "%s %s" without template_name form: ' %  (app_name, widget_name)
                    continue
                if app_name == widget.app_name and widget_name == widget.widget_name:
                    # this is the form of the widget class that the editing widget is of
                    # init the form with the current widgets config, and set the active widget to this one
                    form_dict = dict([(k,v) for k,v in widget.config])
                    context = {'form': form_class(initial=form_dict, group=wc.group)}
                    form_active = True
                else:
                    context = {'form': form_class(group=wc.group)}
                print ">> widg trying to:", app_name, widget_name, widget_class, form_class, form_class.template_name
                widget_form_content = render(request, form_class.template_name, context).content
                data.append({
                    'app_name': app_name,
                    'widget_name': widget_name,
                    'form_content': widget_form_content,
                    'form_id': '%s_%s_%d' % (app_name, widget_name, uuid1()),
                    'form_active': form_active,
                })
        context = {
            'widget_data': data,
            'widget_conf_id': widget.id,
        }
        context.update(extra_context)
        return render(request, template_name, context)


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
        return {'group_id': self.group.pk, 'type': WidgetConfig.TYPE_DASHBOARD}

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
