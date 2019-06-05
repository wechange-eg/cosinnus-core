from __future__ import unicode_literals

from builtins import object
import logging

from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.views.generic import CreateView, DeleteView, UpdateView

from cosinnus.forms.idea import CosinnusIdeaForm
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.idea import CosinnusIdea
from cosinnus.models.tagged import LikeObject
from cosinnus.views.mixins.group import RequireLoggedInMixin, RequireWriteGrouplessMixin
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from ajax_forms.ajax_forms import AjaxFormsDeleteViewMixin


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
    """ Create View for Ideas """
    
    CREATOR_LIKES_OWN_IDEA = True
    
    form_view = 'add'
    
    def get_context_data(self, **kwargs):
        context = super(IdeaCreateView, self).get_context_data(**kwargs)
        context.update({
            'form_view': self.form_view,
        })
        return context
    
    def form_valid(self, form):
        form.instance.creator = self.request.user
        ret = super(IdeaCreateView, self).form_valid(form)
        
        if self.object and self.CREATOR_LIKES_OWN_IDEA:
            # instantly create a like for the new idea from the creator
            content_type = ContentType.objects.get_for_model(CosinnusIdea)
            LikeObject.objects.create(content_type=content_type, object_id=self.object.id, user=self.request.user, liked=True)
            self.object.update_index() # update the idea's index
        return ret
    
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


class IdeaDeleteView(RequireWriteGrouplessMixin, SamePortalGroupMixin, AjaxFormsDeleteViewMixin, 
        DeleteView):

    model = CosinnusIdea
    message_success = _('Your idea was deleted successfully.')
    
    def get_success_url(self):
        # disabled the success message for now as it isn't displayed on the map
        #messages.success(self.request, self.message_success)
        return reverse('cosinnus:idea-list-mine')

idea_delete = IdeaDeleteView.as_view()


