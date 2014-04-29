# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from collections import defaultdict

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from cosinnus.models.tagged import AttachedObject


class FormAttachable(forms.ModelForm):
    """
    Used together with AttachableViewMixin.

    Extending this form will automatically add fields for all attachable
    cosinnus models (as configured in `settings.COSINNUS_ATTACHABLE_OBJECTS`)
    to a form. Even though there is a different field for each attachable
    model, this form handles saving all selected objects to the object's
    `attached_objects` M2M field.
    """
    def __init__(self, *args, **kwargs):
        attachable_objects_sets = kwargs.pop('attached_objects_querysets', {})
        super(FormAttachable, self).__init__(*args, **kwargs)

        preselected = defaultdict(list)
        # retrieve the attached objects ids to select them in the update view
        if self.instance and self.instance.pk:
            for attached in self.instance.attached_objects.all():
                if attached and attached.target_object:
                    preselected[attached.model_name].append(attached.target_object.pk)

        # add a field for each model type of attachable file provided by cosinnus apps
        # each field's name is something like 'attached:cosinnus_file.FileEntry'
        # and fill the field with all available objects for that type (this is passed from our view)
        for model_name, queryset in six.iteritems(attachable_objects_sets):
            initial = preselected[model_name.split('__', 1)[1]]
            model_name = model_name.replace('.', '__')
            self.fields[model_name] = forms.ModelMultipleChoiceField(
                queryset=queryset, required=False, initial=initial, label=_(model_name)
            )

    def save_attachable(self):
        """Called by `AttachableViewMixin.form_valid()`"""
        # we don't want the object to have any attached files other than the
        # ones submitted to the form
        self.instance.attached_objects.clear()

        # Find all attached objects in a saved form (their field values are all
        # something like 'attached:cosinnus_file.FileEntry' and instead of
        # saving them find or create an attachable object for each of the
        # selected objects
        for key, entries in six.iteritems(self.cleaned_data):
            if key.startswith('attached__cosinnus'):
                for attached_obj in entries:
                    object_id = str(attached_obj.pk)
                    content_type = ContentType.objects.get_for_model(attached_obj)
                    (ao, _) = AttachedObject.objects.get_or_create(content_type=content_type, object_id=object_id)
                    self.instance.attached_objects.add(ao)
