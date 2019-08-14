from __future__ import unicode_literals

from builtins import object
import logging

from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.views.generic import CreateView, DeleteView, UpdateView

from cosinnus.views.mixins.group import RequireLoggedInMixin, RequireWriteGrouplessMixin
from django.urls import reverse
from ajax_forms.ajax_forms import AjaxFormsDeleteViewMixin
from cosinnus.views.group import SamePortalGroupMixin
from cosinnus.forms.organization import CosinnusOrganizationForm
from cosinnus.models.organization import CosinnusOrganization
from cosinnus.conf import settings


logger = logging.getLogger('cosinnus')


class CosinnusOrganizationFormMixin(object):
    
    form_class = CosinnusOrganizationForm
    model = CosinnusOrganization
    template_name = 'cosinnus/organization/organization_form.html'
    
    def get_form_kwargs(self):
        kwargs = super(CosinnusOrganizationFormMixin, self).get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def get_context_data(self, **kwargs):
        context = super(CosinnusOrganizationFormMixin, self).get_context_data(**kwargs)
        context.update({
        })
        return context
    
    def form_valid(self, *args, **kwargs):
        ret = super(CosinnusOrganizationFormMixin, self).form_valid(*args, **kwargs)
        self.object.update_index()
        return ret
    

class OrganizationCreateView(RequireLoggedInMixin, CosinnusOrganizationFormMixin, CreateView):
    """ Create View for Organizations """
    
    form_view = 'add'
    
    def get_context_data(self, **kwargs):
        context = super(OrganizationCreateView, self).get_context_data(**kwargs)
        context.update({
            'form_view': self.form_view,
        })
        return context
    
    def form_valid(self, form):
        form.instance.creator = self.request.user
        # set default values
        for key, val in getattr(settings, 'COSINNUS_ORGANIZATION_DEFAULT_SETTINGS', {}):
            setattr(form.instance, key, val)
        ret = super(OrganizationCreateView, self).form_valid(form)
        return ret
    
    def get_success_url(self):
        return self.object.get_absolute_url() + '&action=create'
    
organization_create = OrganizationCreateView.as_view()


class OrganizationEditView(RequireWriteGrouplessMixin, CosinnusOrganizationFormMixin, UpdateView):

    form_view = 'edit'
    
    def get_context_data(self, **kwargs):
        context = super(OrganizationEditView, self).get_context_data(**kwargs)
        context.update({
            'form_view': self.form_view,
        })
        return context

    def get_success_url(self):
        return self.object.get_absolute_url() + '&action=edit'
    
organization_edit = OrganizationEditView.as_view()


class OrganizationDeleteView(RequireWriteGrouplessMixin, SamePortalGroupMixin, AjaxFormsDeleteViewMixin, 
        DeleteView):

    model = CosinnusOrganization
    message_success = _('Your organization was deleted successfully.')
    
    def get_success_url(self):
        # disabled the success message for now as it isn't displayed on the map
        #messages.success(self.request, self.message_success)
        return reverse('cosinnus:organization-list-mine')

organization_delete = OrganizationDeleteView.as_view()

