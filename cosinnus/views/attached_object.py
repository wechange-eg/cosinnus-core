# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db.models.loading import get_model
from django.http.response import HttpResponseRedirect
from django.views.generic.edit import CreateView, UpdateView

from cosinnus.core.loaders.attached_objects import cosinnus_attached_object_registry as caor


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
        attachable_objects = caor.attachable_to.get(source_model_id, [])

        # for each type of allowed attachable object model, find all instances of
        # this model in the current group, and pass them to the FormAttachable,
        # so fields can be created and filled
        querysets = dict()
        for attach_model_id in attachable_objects:
            app_label, model_name = attach_model_id.split('.')
            attach_model_class = get_model(app_label, model_name)
            queryset = attach_model_class._default_manager.filter(group=self.group)
            querysets['attached:' + attach_model_id] = queryset

        # pass all attachable cosinnus models to FormAttachable via kwargs
        kwargs.update({'attached_files_querysets': querysets})
        return kwargs

    def form_valid(self, form):
        # retrieve the attached objects from the form and save them
        # after saving the object itself
        self.object.save()
        if hasattr(form, 'save_m2m'):
            form.save_m2m()
        form.save_attachable()
        return HttpResponseRedirect(self.get_success_url())


class CreateViewAttachable(AttachableViewMixin, CreateView):
    pass


class UpdateViewAttachable(AttachableViewMixin, UpdateView):
    pass
