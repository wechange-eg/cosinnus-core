# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse
from django.views.generic import CreateView
from django.utils.translation import ugettext_lazy as _

from cosinnus.forms.hierarchy import AddContainerForm
from cosinnus.views.mixins.group import (RequireWriteMixin, FilterGroupMixin,
    RequireCreateObjectsInMixin)
from cosinnus.views.mixins.tagged import HierarchyPathMixin
from cosinnus.utils.urls import group_aware_reverse
from django.views.generic.base import View
from django.http.response import HttpResponseBadRequest, HttpResponse,\
    HttpResponseServerError
from django.shortcuts import get_object_or_404
from django.http.response import JsonResponse
from cosinnus.templatetags.cosinnus_tags import has_write_access
from cosinnus.utils.permissions import check_object_write_access
from annoying.functions import get_object_or_None


class AddContainerView(RequireWriteMixin, FilterGroupMixin,
        HierarchyPathMixin, CreateView):
    """
    View to add containers in the hierarchy

    Child classes are required to define attributes 'model' and 'appname'
    """
    template_name = 'cosinnus/hierarchy/add_container.html'

    def __init__(self, *args, **kwargs):
        if not self.appname:
            raise ImproperlyConfigured(_('No appname given for adding containers.'))
        super(AddContainerView, self).__init__(*args, **kwargs)

    def get_success_url(self):
        return group_aware_reverse('cosinnus:%s:list' % self.appname,
                       kwargs={'group': self.group})

    def get_form(self, form_class=None):
        """Override get_form to use model-specific form"""
        class ModelAddContainerForm(AddContainerForm):
            class Meta(AddContainerForm.Meta):
                model = self.model
        form_class = ModelAddContainerForm
        return super(AddContainerView, self).get_form(form_class)

    def form_valid(self, form):
        """
        If the form is valid, we need to do the following:
        - Set instance's is_container to True
        - Set the instance's group
        - Set the path again once the slug has been established
        """
        form.instance.is_container = True
        form.instance.group = self.group
        ret = super(AddContainerView, self).form_valid(form)

        # only after this save do we know the final slug
        # we still must add it to the end of our path if we're saving a container
        self.object.path += self.object.slug + '/'
        self.object.save()

        return ret

    def get_context_data(self, *args, **kwargs):
        context = super(AddContainerView, self).get_context_data(*args, **kwargs)
        context['cancel_url'] = group_aware_reverse('cosinnus:%s:list' % self.appname,
            kwargs={'group': self.group})
        return context


class MoveElementView(RequireCreateObjectsInMixin, View):
    """ Moves one or more superclass elements of HierarchicalBaseTaggableObject to a different folder.
        
        This is a pseudo-abstract class, superclass this with your own view for each cosinnus app.
        Requires `model` to be set to a non-abstract HierarchicalBaseTaggableObject model.
        Expects to find a `group` kwarg.
        Excpects `element_ids[]` and `target_folder_id` as POST arguments.
     """
    
    http_method_names = ['post', ]
    
    model = None
    # if folder_model==None, model will be used
    folder_model = None
    
    def post(self, request, *args, **kwargs):
        if not self.model:
            raise ImproperlyConfigured('No model class is set for the pseudo-abstract view MoveElementView.')
        
        element_ids = request.POST.getlist('element_ids[]', [])
        target_folder_id = request.POST.get('target_folder_id', None)
        
        if not (element_ids or target_folder_id or self.group):
            return HttpResponseBadRequest('Missing POST fields for this request.')
        
        successful_ids = []
        target_folder = get_object_or_404(self.folder_model or self.model, id=target_folder_id, group=self.group)
        for element_id in element_ids:
            element = get_object_or_None(self.model, id=element_id, group=self.group)
            
            # check write permission on element
            if not check_object_write_access(element, request.user):
                continue
            if self.move_element(element, target_folder):
                successful_ids.append(element_id)
        
        data = {
            'had_errors': len(successful_ids) != len(element_ids),
            'successful_ids': successful_ids,
        }
        return JsonResponse(data)
        
        
    def move_element(self, element, target_folder):
        if element.is_container:
            raise HttpResponseBadRequest('Container moving is not yet implemented!')
        elif not element.path == target_folder.path:
            element.path = target_folder.path
            element.save()
            return True
        return False
        
        
