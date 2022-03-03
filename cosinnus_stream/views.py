# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
from builtins import object
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.views.generic.detail import DetailView

from cosinnus.core.registries import attached_object_registry as aor
from cosinnus_stream.models import Stream
from cosinnus.views.mixins.user import UserFormKwargsMixin
from cosinnus_stream.forms import StreamForm
from django.contrib import messages
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.http.response import HttpResponseRedirect
from django.urls import reverse_lazy, reverse
from cosinnus.templatetags.cosinnus_tags import has_write_access
from cosinnus.core.decorators.views import redirect_to_403
from cosinnus.models.group import CosinnusGroup, CosinnusPortal,\
    CosinnusPortalMembership
from cosinnus.models import MEMBER_STATUS
from cosinnus.views.widget import DashboardWidgetMixin
from django.shortcuts import get_object_or_404, redirect
from cosinnus.conf import settings


class StreamsMixin(object):
        
    def get_streams(self):
        if not self.request.user.is_authenticated:
            return self.model._default_manager.none()
        qs = self.model._default_manager.filter(creator__id=self.request.user.id, is_my_stream__exact=False).order_by('-is_special')
        return qs


class StreamDetailView(DashboardWidgetMixin, StreamsMixin, DetailView):
    model = Stream
    template_name = 'cosinnus_stream/stream_detail.html'
    
    # any 'app_name.widget_name' entries in here will be filtered out of the context_data
    disallowed_widgets = ['stream.my_streams', 'note.detailed_news_list', 'etherpad.latest', 'cosinnus.group_members']
    
    default_widget_order = ['todo.mine', 'event.upcoming']
    
    
    def dispatch(self, request, *args, **kwargs):
        if getattr(settings, 'COSINNUS_USE_V2_DASHBOARD', False) or \
            (getattr(settings, 'COSINNUS_USE_V2_DASHBOARD_ADMIN_ONLY', False) and self.request.user.is_superuser):
            return redirect('cosinnus:user-dashboard')
        
        return super(StreamDetailView, self).dispatch(request, *args, **kwargs)
    
    def get_filter(self):
        """ Submit the user id so queryset elements can be filtered for that user. """
        
        # anonymous users do not see any widgets
        if not self.request.user.is_authenticated:
            return {'id': -1}
        
        return {'user_id': self.request.user.pk}
    
    def get_object(self, queryset=None):
        """ Allow queries without slug or pk """
        if self.request.user.is_authenticated and (self.pk_url_kwarg in self.kwargs or self.slug_url_kwarg in self.kwargs):
            queryset = queryset or self.model.objects.all()
            if self.pk_url_kwarg in self.kwargs:
                self.object = get_object_or_404(self.model, id=self.kwargs.get(self.pk_url_kwarg))
            if self.slug_url_kwarg in self.kwargs:
                self.object = get_object_or_404(self.model, slug=self.kwargs.get(self.slug_url_kwarg), creator=self.request.user)
            
        if not hasattr(self, 'object'):
            # no object supplied means we want to access the "MyStream".
            # decide if we want the all-portal or a portal-specific Stream by URL kwargs
            if self.kwargs.get('is_all_portals', False):
                portals = ''
            else:
                portals = str(CosinnusPortal.get_current().id)
            
            if not self.request.user.is_authenticated:
                # for guests, return a virtual stream
                self.object = self.model(is_my_stream=True, portals=portals)
            else:
                self.object = self.model._default_manager.get_my_stream_for_user(self.request.user, portals=portals)
        return self.object
    
    def check_permissions(self):
        if self.object and hasattr(self.object, 'creator') and not self.object.creator == self.request.user:
            raise PermissionDenied(_('You do not have permission to access this stream.'))
        
    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.check_permissions()
        
        self.objects = self.object.get_stream_objects_for_user(self.request.user, \
                           include_public=bool(int(request.GET.get('show_public', "0"))))
        self.streams = self.get_streams()
        
        # save last_seen date and set it to current
        self.last_seen = self.object.last_seen_safe
        if request.user.is_authenticated:
            self.object.set_last_seen()
        
        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)
    
    
    def get_context_data(self, **kwargs):
        kwargs.update({
            'total_count': self.object.total_count,
            'has_more': self.object.has_more,
            'has_more_count': max(0, self.object.total_count - len(self.objects)),
            'last_seen': self.last_seen,
            'stream': self.object,
            'stream_objects': self.objects,
            'streams': self.streams,
        })
        return super(StreamDetailView, self).get_context_data(**kwargs)

stream_detail = StreamDetailView.as_view()


class StreamFilterForUserMixin(object):
    """ Filters the queryset for only streams of the current user """
    
    def get_queryset(self):
        qs = super(StreamFilterForUserMixin, self).get_queryset()
        qs = qs.filter(creator=self.request.user)
        return qs

class StreamFormMixin(object):
    
    form_class = StreamForm
    model = Stream
    template_name = 'cosinnus_stream/stream_form.html'
    
    def get_form(self, *args, **kwargs):
        """
        Filter the groups displayed to the user to be his groups/public groups.
        """
        form = super(StreamFormMixin, self).get_form( *args, **kwargs)
        group_qs = CosinnusGroup.objects.filter(\
                id__in=CosinnusGroup.objects.get_for_user_pks(self.request.user, include_public=True)).\
                order_by('public')
        group_qs = group_qs.filter(portal=CosinnusPortal.get_current())
        
        # enable this to show groups from all portals the user is a member in!
        #user_portals = list(CosinnusPortalMembership.objects.filter(user=self.request.user, status__in=MEMBER_STATUS).values_list('group__id', flat=True))
        #group_qs = group_qs.filter(portal__id__in=user_portals)
        
        form.forms['obj'].fields['group'].queryset = group_qs
        
        return form
    
    def get_context_data(self, **kwargs):
        context = super(StreamFormMixin, self).get_context_data(**kwargs)
        
        used_renderers = []
        model_selection = []
        for model_name in aor:
            # skip non-cosinnus app models
            if not model_name.startswith('cosinnus'):
                continue
            # skip secondary sub-objects in an app that use the same renderer 
            # as a model already included in the options (as they would be redundant)
            if aor[model_name] in used_renderers:
                continue
            
            # label for the checkbox is the app identifier translation
            app = model_name.split('.')[0].split('_')[-1]
            model_selection.append({
                'model_name': model_name,
                'app': app,
                'label': pgettext_lazy('the_app', app),
                'checked': True if (not self.object or not self.object.models) else model_name in self.object.models,
            })
            used_renderers.append(aor[model_name])
        
        context.update({
            'stream_model_selection': model_selection,
            'streams': self.get_streams(),
            'form_view': self.form_view,
        })
        return context
    
    def form_valid(self, form):
        form.instance.creator = self.request.user
        messages.success(self.request, self.message_success)
        return super(StreamFormMixin, self).form_valid(form)
    
    def get_success_url(self):
        return self.object.get_absolute_url()
    

class StreamCreateView(UserFormKwargsMixin, StreamsMixin, StreamFormMixin, CreateView):

    form_view = "add"
    message_success = _('Your stream was added successfully.')
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, _('Please log in to access this page.'))
            return HttpResponseRedirect(reverse_lazy('login') + '?next=' + request.path)
        return super(StreamCreateView, self).dispatch(request, *args, **kwargs)
    

stream_create = StreamCreateView.as_view()


class StreamUpdateView(UserFormKwargsMixin, StreamFilterForUserMixin, StreamsMixin, StreamFormMixin, UpdateView):

    form_view = "edit"
    message_success = _('Your stream was updated successfully.')
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, _('Please log in to access this page.'))
            return HttpResponseRedirect(reverse_lazy('login') + '?next=' + request.path)
        elif not has_write_access(request.user, self.get_object()):
            return redirect_to_403(request)
        return super(StreamUpdateView, self).dispatch(request, *args, **kwargs)
    
    def get_object(self, queryset=None):
        if hasattr(self, 'object'):
            return self.object
        return super(StreamUpdateView, self).get_object(queryset)

stream_update = StreamUpdateView.as_view()



class StreamDeleteView(UserFormKwargsMixin, StreamFilterForUserMixin, DeleteView):

    model = Stream
    message_success = _('Your stream was deleted successfully.')
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, _('Please log in to access this page.'))
            return HttpResponseRedirect(reverse_lazy('login') + '?next=' + request.path)
        
        self.object = self.get_object()
        if not has_write_access(request.user, self.object):
            return redirect_to_403(request)
        
        if self.object.is_my_stream:
            messages.error(request, _('You cannot delete the default stream!'))
            return HttpResponseRedirect(reverse('cosinnus:my_stream'))
        
        return super(StreamDeleteView, self).dispatch(request, *args, **kwargs)
    
    def get_success_url(self):
        messages.success(self.request, self.message_success)
        return reverse('cosinnus:my_stream')

stream_delete = StreamDeleteView.as_view()

