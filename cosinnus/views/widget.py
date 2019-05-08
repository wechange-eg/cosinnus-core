# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
import six

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render,\
    redirect
from django.template import RequestContext
from django.utils.decorators import method_decorator
from django.utils.encoding import force_text
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic import TemplateView

from cosinnus.core.decorators.views import require_admin_access_decorator,\
    redirect_to_not_logged_in
from cosinnus.core.registries import widget_registry
from cosinnus.models.widget import WidgetConfig
from cosinnus.utils.http import JSONResponse
from cosinnus.utils.permissions import check_ug_admin, check_ug_membership,\
    check_user_superuser, check_object_write_access
from cosinnus.views.mixins.group import RequireReadOrRedirectMixin,\
    GroupObjectCountMixin
from uuid import uuid1
from cosinnus.core.registries.apps import app_registry
from cosinnus.utils.functions import resolve_class
from cosinnus.utils.urls import group_aware_reverse
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse_lazy, reverse
from cosinnus.utils.user import ensure_user_widget
from django.http.response import HttpResponseNotAllowed, JsonResponse
from cosinnus.conf import settings


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
        widget_class = widget_registry.get(app_name, widget_name)
        if widget_class is None:
            return render('cosinnus/widgets/not_found.html')
        form_class = widget_class.get_setup_form_class()
        if not widget_class.allow_on_group:
            return render('cosinnus/widgets/not_allowed_group.html')
        
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
        form_active = True
        for app_name, widgets in widget_registry:
            for widget_name in widgets:
                widget_class = widget_registry.get(app_name, widget_name)
                if widget_class is None:
                    #print ">>>>widg not found:", app_name, widget_name
                    continue
                form_class = widget_class.get_setup_form_class()
                if not getattr(form_class, "template_name", None):
                    #raise ImproperlyConfigured('Widget form "%s %s" has no attribute "template_name" configured!' % (app_name, widget_name))
                    #print '>> ignoring widget "%s %s" without template_name form: ' %  (app_name, widget_name)
                    continue
                context = {'form': form_class(group=group)}
                widget_form_content = render(request, form_class.template_name, context).content
                data.append({
                    'app_name': app_name,
                    'widget_name': widget_name,
                    'widget_title': widget_class.get_widget_title(),
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
    if not check_user_superuser(request.user) and \
             wc.group and not (check_ug_membership(request.user, wc.group) or \
             wc.group.public or wc.type == WidgetConfig.TYPE_MICROSITE) or \
             wc.user and wc.user_id != request.user.pk:
        return HttpResponseForbidden('Access denied!')
    widget_class = widget_registry.get(wc.app_name, wc.widget_name)
    if widget_class is None:
        return render('cosinnus/widgets/not_found.html')
    widget = widget_class(request, wc)
    widget_content, rows_returned, has_more = widget.get_data(int(offset))
    
    data = {
        'X-Cosinnus-Widget-Content': widget_content,
        'X-Cosinnus-Widget-Title': force_text(widget.title),
        'X-Cosinnus-Widget-App-Name': force_text(wc.app_name),
        'X-Cosinnus-Widget-Widget-Name': force_text(wc.widget_name),
        'X-Cosinnus-Widget-Num-Rows-Returned': rows_returned,
        'X-Cosinnus-Widget-Has-More-Data': 'true' if has_more else 'false',
    }
    title_url = widget.title_url
    if title_url is not None:
        data['X-Cosinnus-Widget-Title-URL'] = force_text(title_url)
    
    return JSONResponse(data)


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
        return render('cosinnus/widgets/delete.html', c.flatten())


@ensure_csrf_cookie
def widget_edit(request, id, app_name=None, widget_name=None):
    template_name = 'cosinnus/widgets/add_widget.html'
    extra_context = {'form_view': 'edit'}
    
    wc = get_object_or_404(WidgetConfig, id=int(id))
    if wc.group and not check_ug_admin(request.user, wc.group) or \
            wc.user and wc.user_id != request.user.pk:
        return HttpResponseForbidden('Access denied!')
    
    if app_name and widget_name and (wc.app_name != app_name or wc.widget_name != widget_name):
        #print ">>>>> THIS WIDGET WAS SET UP TO BE SWAPPED BY EDITING IT!"
        #print ">> TODO: create new widget using create function, transfer important values, then delete this widget! "
        # TODO: widget swapping disabled for now!
        raise Exception("Swapping of widget types is not enabled. \
            Delete this widget and create a new one if you want one of a different type!")
    
    widget_class = widget_registry.get(wc.app_name, wc.widget_name)
    if widget_class is None:
        return render('cosinnus/widgets/not_found.html')
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
                    #print ">>>>widg not found:", app_name, widget_name
                    continue
                form_class = widget_class.get_setup_form_class()
                if not getattr(form_class, "template_name", None):
                    #raise ImproperlyConfigured('Widget form "%s %s" has no attribute "template_name" configured!' % (app_name, widget_name))
                    #print '>> ignoring widget "%s %s" without template_name form: ' %  (app_name, widget_name)
                    continue
                if app_name == widget.app_name and widget_name == widget.widget_name:
                    # this is the form of the widget class that the editing widget is of
                    # init the form with the current widgets config, and set the active widget to this one
                    form_dict = dict([(k,v) for k,v in widget.config])
                    form_dict.update({
                        'sort_field': widget.config.sort_field,
                    })
                    context = {'form': form_class(initial=form_dict, group=wc.group)}
                    form_active = True
                else:
                    # TODO: widget swapping disabled for now!
                    continue
                    #context = {'form': form_class(group=wc.group)}
                widget_form_content = render(request, form_class.template_name, context).content
                data.append({
                    'app_name': app_name,
                    'widget_name': widget_name,
                    'widget_title': widget_class.get_widget_title(),
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


class DashboardWidgetMixin(object):
    
    # any 'app_name.widget_name' entries in here will be filtered out of the context_data
    disallowed_widgets = []
    # fallback ordering of 'app_name.widget_name' for when some widgets have the same sort_field value
    default_widget_order = ['note.detailed_news_list', 'event.upcoming', 
                            'todo.mine', 'etherpad.latest', 'cosinnus.group_members', 'cosinnus.group_projects']
    
    
    def reorder_equal_widgets(self, widgets):
        """ Sorts all widgets with equal sort_key by their default_widget_order """
        if not self.default_widget_order:
            return widgets
        
        def sort_key(widget):
            try:
                return self.default_widget_order.index("%s.%s" % (widget.config.app_name, widget.config.widget_name.replace(" ", "_")))
            except ValueError:
                return 999
        
        sort_fields = sorted(list(set([widget.config.sort_field for widget in widgets])))
        grouped_widgets = [[widget for widget in widgets if widget.config.sort_field == rank] for rank in sort_fields]
        
        sorted_widgets = []
        for group in grouped_widgets:
            group = sorted(group, key=sort_key)
            sorted_widgets.extend(group)
            """
            for preference in self.default_widget_order:
                for i in reversed(range(len(group))):
                    widg = group[i]
                    if "%s.%s" % (widg.config.app_name, widg.config.widget_name.replace(" ", "_")) == preference:
                        sorted_widgets.append(widg)
                        del group[i]
            sorted_widgets.extend(group)
            """
        return sorted_widgets
    
    def get_context_data(self, **kwargs):
        widget_filter = self.get_filter()
        widgets_configs = WidgetConfig.objects.filter(**widget_filter).order_by('sort_field')
        
        deactivated_apps = []
        if 'group_id' in widget_filter:
            # if we are dealing with group dashboard widgets, use the group's deactivated apps
            deactivated_apps = self.group.get_deactivated_apps()
        
        widgets = []
        """ We also sort each unique widget into the context to be accessed hard-coded"""
        for wc in widgets_configs:
            # check deactivated apps to see if widget can't be shown:
            if 'cosinnus_%s' % wc.app_name in deactivated_apps:
                continue
            # check block list for disallowed widgets (from overriding views)
            if "%s.%s" % (wc.app_name, wc.widget_name.replace(" ", "_")) in self.disallowed_widgets:
                continue
            
            widget_class = widget_registry.get(wc.app_name, wc.widget_name)
            if widget_class:
                widget = widget_class(self.request, wc)
                widgets.append(widget)
        
        widgets = self.reorder_equal_widgets(widgets)
        kwargs.update({
            'widgets': widgets,
        })
    
        return super(DashboardWidgetMixin, self).get_context_data(**kwargs)


class GroupDashboard(RequireReadOrRedirectMixin, DashboardWidgetMixin, GroupObjectCountMixin, TemplateView):
    
    template_name = 'cosinnus/dashboard.html'
    
    def get_filter(self):
        return {'group_id': self.group.pk, 'type': WidgetConfig.TYPE_DASHBOARD}

    
    def on_error(self, request, *args, **kwargs):
        """ Called when the require-read permission is not met """
        if not request.user.is_authenticated:
            return redirect_to_not_logged_in(request, view=self)
        messages.warning(request, _('You are not currently a member of %s! If you wish you can request to become a member below.') % self.group.name)
        return redirect(group_aware_reverse('cosinnus:group-list-filtered', kwargs={'group': kwargs.get('group')}))
    

group_dashboard = GroupDashboard.as_view()


def save_widget_config(request):
    """ Save-endpoint WidgetConfig priorities for dashboard widget rearranging """
    
    user = request.user
    if not user.is_authenticated:
        return HttpResponseForbidden()
    
    if not request.is_ajax() or not request.method=='POST':
        return HttpResponseNotAllowed(['POST'])
    
    import json
    widgets = json.loads(request.POST.get('widget_data'))
    for widget_id, props in list(widgets.items()):
        if 'priority' in props:
            try:
                wc = WidgetConfig.objects.get(id=int(widget_id))
                
                if (wc.group and check_object_write_access(wc.group, user)) or \
                    (wc.user and wc.user.id == user.id):
                    wc.sort_field = props.get('priority')
                    wc.save()
            except WidgetConfig.DoesNotExist:
                pass
    
    messages.info(request, _('Your changes have been saved.'))
    
    return JsonResponse({'status': 'ok'}, safe=False)

