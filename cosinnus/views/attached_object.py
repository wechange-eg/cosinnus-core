# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models.loading import get_model
from django.views.generic.edit import CreateView, UpdateView

from cosinnus.core.registries import attached_object_registry
from django_select2.views import Select2View, NO_ERR_RESP
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from cosinnus.models.group import CosinnusGroup
from cosinnus.views.mixins.group import RequireReadMixin
from cosinnus.conf import settings
from cosinnus.models.tagged import BaseHierarchicalTaggableObjectModel
from django.template.loader import render_to_string
from django.utils.html import escape
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user


def build_attachment_field_result(obj_type, obj):
    """ Builds a result that can be fed into a django select2 field """
    # we're looking for the template 'attached_object_select_pill.html' in the cosinnus app's template folder
    pill_template = '%s/attached_object_select_pill.html' % obj_type.split('.')[0]
    pill_html = render_to_string(pill_template, {'type':obj_type,'text':escape(obj.title)})
    ret =(obj_type+":"+str(obj.id), pill_html,) 
    return ret
        

class AttachableViewMixin(object):
    """
    Used together with FormAttachableMixin.

    Extending this view will add form fields for Cosinnus attachable objects to
    `CreateView`s and `UpdateView`s. Configure which cosinnus objects may be
    attached to your object in `settings.COSINNUS_ATTACHABLE_OBJECTS`.
    """

    def form_valid(self, form):
        # retrieve the attached objects from the form and save them
        # after saving the object itself
        ret = super(AttachableViewMixin, self).form_valid(form)
        # if hasattr(form, 'save_m2m'):
        #     form.save_m2m()
        form.save_attachable()
        return ret

    def forms_valid(self, form, inlines):
        # retrieve the attached objects from the form and save them
        # after saving the object itself
        ret = super(AttachableViewMixin, self).forms_valid(form, inlines)
        # if hasattr(form, 'save_m2m'):
        #     form.save_m2m()
        form.save_attachable()
        return ret


class CreateViewAttachable(AttachableViewMixin, CreateView):
    pass


class UpdateViewAttachable(AttachableViewMixin, UpdateView):
    pass


class AttachableObjectSelect2View(RequireReadMixin, Select2View):
    """
        This view is used as API backend to serve the suggestions for the message recipient field.
        
        For each model type use the search terms to both search in the attachable model types 
        (that is, their configured type aliases (see settings.COSINNUS_ATTACHABLE_OBJECTS_SUGGEST_ALIASES))
        and their title for good matches.
        
        Examples (assumed that 'event' is configured as an alias for [cosinnus_event.Event]: 
            term: 'even Heilig' would return an [Event] with title 'Heiligabendfeier'
            term: 'even Heilig' would not find a [File] with title 'Einladung zum Heiligabend'
            term  'even Heilig' would (!) return a [File] with title 'Invitiation: Heiligabend-Event.pdf'
    """
    def check_all_permissions(self, request, *args, **kwargs):
        user = request.user 
        
        # Check if current user is member of this group
        current_group = self.kwargs.get('group', None)
        usergroups = CosinnusGroup.objects.get_for_user(request.user)
        is_member = any((current_group == group.slug) for group in usergroups)
        
        if not user.is_authenticated() or not is_member:
            raise PermissionDenied
        
    def get_results(self, request, term, page, context):
        tokens = term.lower().split()
        aliases_dict = settings.COSINNUS_ATTACHABLE_OBJECTS_SUGGEST_ALIASES
        
        results = []
       
        attach_models = []
        if 'model_as_target' in self.request.GET: 
            attach_models = self.kwargs.get('model', '').split(',')
        else:
            attach_models = attached_object_registry.get_attachable_to(self.kwargs.get('model', None))
       
        for attach_model_id in attach_models:
            aliases = aliases_dict.get(attach_model_id, [])
            aliases = '||'.join(aliases)
            
            app_label, model_name = attach_model_id.split('.')
            attach_model_class = get_model(app_label, model_name)
            if BaseHierarchicalTaggableObjectModel in attach_model_class.__bases__:
                queryset = attach_model_class._default_manager.filter(group__slug=self.kwargs.get('group', None), is_container=False)
            else:
                queryset = attach_model_class._default_manager.filter(group__slug=self.kwargs.get('group', None))
            
            queryset = filter_tagged_object_queryset_for_user(queryset, self.request.user)
            
            """ For each token in the search query, filter the full object queryset further down,
                comparing the titles of these objects, unless: the query is in the special aliases list
                for that model type (for example 'eve' matches 'events', which is a special alias of 
                cosinnus_event.Event, and thus only further restrict-filters objects that are not events. """
            for token in tokens:
                if not token in aliases:
                    queryset = queryset.filter(Q(title__icontains=token))
            
            # these result sets are what select2 uses to build the choice list
            for result in queryset:
                results.append( build_attachment_field_result(attach_model_id, result))
            
        return (NO_ERR_RESP, False, results) # Any error response, Has more results, options list

attachable_object_select2_view = AttachableObjectSelect2View.as_view()
