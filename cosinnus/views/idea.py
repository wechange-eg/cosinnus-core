from __future__ import unicode_literals

import logging

from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.views.generic import CreateView, DeleteView, UpdateView
from django.views.generic.base import RedirectView

from cosinnus.forms.idea import CosinnusIdeaForm
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.idea import CosinnusIdea
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.views.mixins.group import RequireLoggedInMixin, RequireWriteGrouplessMixin


logger = logging.getLogger('cosinnus')


class SamePortalGroupMixin(object):

    def get_queryset(self):
        """
        Filter the queryset for this portal only!
        """
        return super(SamePortalGroupMixin, self).get_queryset().filter(portal=CosinnusPortal.get_current())


class CosinnusIdeaFormMixin(object):
    
    form_class = CosinnusIdeaForm
    model = CosinnusIdea
    template_name = 'cosinnus/idea/idea_form.html'
    
    def get_form_kwargs(self):
        kwargs = super(CosinnusIdeaFormMixin, self).get_form_kwargs()
        #kwargs['request'] = self.request
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super(CosinnusIdeaFormMixin, self).get_context_data(**kwargs)
        context.update({
        })
        return context
    

class IdeaCreateView(RequireLoggedInMixin, CosinnusIdeaFormMixin, CreateView):
    
    form_view = 'add'
    
    def get_context_data(self, **kwargs):
        context = super(IdeaCreateView, self).get_context_data(**kwargs)
        context.update({
            'form_view': self.form_view,
        })
        return context
    
    def form_valid(self, form):
        form.instance.creator = self.request.user
        return super(IdeaCreateView, self).form_valid(form)
    
    def get_success_url(self):
        return self.object.get_absolute_url() + '&action=create'
    
idea_create = IdeaCreateView.as_view()


class IdeaEditView(RequireWriteGrouplessMixin, CosinnusIdeaFormMixin, UpdateView):

    form_view = 'edit'
    
    def get_context_data(self, **kwargs):
        context = super(IdeaEditView, self).get_context_data(**kwargs)
        context.update({
            'form_view': self.form_view,
        })
        return context

    def get_success_url(self):
        return self.object.get_absolute_url() + '&action=edit'
    

idea_edit = IdeaEditView.as_view()


class IdeaDeleteView(RequireWriteGrouplessMixin, SamePortalGroupMixin, DeleteView):

    model = CosinnusIdea
    message_success = _('Your idea was deleted successfully.')
    
    def get_success_url(self):
        messages.success(self.request, self.message_success)
        return group_aware_reverse('cosinnus:idea-list-mine')

idea_delete = IdeaDeleteView.as_view()


class IdeaListView(RedirectView):
    permanent = False
    
    def get_redirect_url(self, *args, **kwargs):
        return ('/TODO-idea-list')
    
idea_list = IdeaListView.as_view()


class IdeaListMineView(RedirectView):
    permanent = False
    
    def get_redirect_url(self, *args, **kwargs):
        return ('/TODO-idea-mine-list')
    
idea_list_mine = IdeaListMineView.as_view()


