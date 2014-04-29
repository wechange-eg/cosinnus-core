# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models.loading import get_model
from django.views.generic.edit import CreateView, UpdateView

from cosinnus.core.registries import attached_object_registry
from django_select2.views import Select2View, NO_ERR_RESP
from django.db.models import Q
from django.core.exceptions import PermissionDenied
from cosinnus.models.group import CosinnusGroup
from django.contrib.auth.models import User
from cosinnus.views.mixins.group import RequireReadMixin, FilterGroupMixin,\
    GroupFormKwargsMixin
from cosinnus.views.mixins.user import UserFormKwargsMixin


class AttachableViewMixin(object):
    """
    Used together with FormAttachable.

    Extending this view will add form fields for Cosinnus attachable objects to
    `CreateView`s and `UpdateView`s. Configure which cosinnus objects may be
    attached to your object in `settings.COSINNUS_ATTACHABLE_OBJECTS`.
    """
    def get_form_kwargs(self):
        kwargs = super(AttachableViewMixin, self).get_form_kwargs()
        source_model_id = self.model._meta.app_label + '.' + self.model._meta.object_name

        # for each type of allowed attachable object model, find all instances of
        # this model in the current group, and pass them to the FormAttachable,
        # so fields can be created and filled
        querysets = {}
        for attach_model_id in attached_object_registry.get_attachable_to(source_model_id):
            app_label, model_name = attach_model_id.split('.')
            attach_model_class = get_model(app_label, model_name)
            queryset = attach_model_class._default_manager.filter(group=self.group)
            querysets['attached__' + attach_model_id] = queryset

        # pass all attachable cosinnus models to FormAttachable via kwargs
        kwargs.update({'attached_objects_querysets': querysets})
        return kwargs

    def form_valid(self, form):
        # retrieve the attached objects from the form and save them
        # after saving the object itself
        ret = super(AttachableViewMixin, self).form_valid(form)
        # if hasattr(form, 'save_m2m'):
        #     form.save_m2m()
        form.save_attachable()
        return ret


class CreateViewAttachable(AttachableViewMixin, CreateView):
    pass


class UpdateViewAttachable(AttachableViewMixin, UpdateView):
    pass


class AttachableObjectSelect2View(Select2View, RequireReadMixin, GroupFormKwargsMixin,
                     UserFormKwargsMixin):
    """
        This view is used as API backend to serve the suggestions for the message recipient field.
    """
    def check_all_permissions(self, request, *args, **kwargs):
        user = request.user 
        if not user.is_authenticated():
            raise PermissionDenied
        
    def get_results(self, request, term, page, context):
        term = term.lower() 
        print ">>> term:", term
        
        import ipdb; ipdb.set_trace();
        
        # username is not used as filter for the term for now, might confuse users why a search result is found
        users = User.objects.filter( Q(first_name__icontains=term) | Q(last_name__icontains=term))# | Q(username__icontains=term))
        # filter all groups the user is a member of, and all public groups for the term
        # use CosinnusGroup.objects.get_cached() to search in all groups instead
        groups = set(CosinnusGroup.objects.get_for_user(request.user)).union(CosinnusGroup.objects.public())
        groups = [ group for group in groups if term in group.name.lower() ]
        
        # these result sets are what select2 uses to build the choice list
        results = [ ("user:"+str(user.id), "%s %s" % (user.first_name, user.last_name),) for user in users ]
        results.extend([ ("group:"+str(group.id), "[[ %s ]]" % (group.name),) for group in groups ])
        
        return (NO_ERR_RESP, False, results) # Any error response, Has more results, options list

