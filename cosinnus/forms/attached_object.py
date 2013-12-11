# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django import forms
from cosinnus.models.tagged import AttachedObject
from django.contrib.contenttypes.models import ContentType

class FormAttachable(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        attached_sets = kwargs.pop('attached_files_querysets', None)
        super(FormAttachable, self).__init__(*args, **kwargs)

        print(">>> query_sets passed forward:")
        print(attached_sets)

        for model_name, queryset in attached_sets.items():
            self.fields[model_name] = forms.ModelMultipleChoiceField(queryset=queryset, required=False)  # ,label='FFFFFUUUU')
            """ TODO: add initial """
            # self.initial[model_name] = <file.pk of the files that are linked by the instances attached_objects>


    def save_attachable(self):

        print (">>> Now in the save func: instance is:")
        print(self.instance)
        print (">>> cleaned data")
        print(self.cleaned_data)


        """ TODO: save attached_objects to instance """
       # import ipdb; ipdb.set_trace();

        for key, entries in self.cleaned_data.items():
            if key.startswith('attached_cosinnus'):
                for attached_obj in entries:
                    print(">>> Found a fitting object with key " + key)
                    print(attached_obj)
                    object_id = str(attached_obj.pk)
                    content_type = ContentType.objects.get_for_model(attached_obj)

                    print(object_id)
                    print(content_type)
                    (ao, created) = AttachedObject.objects.get_or_create(content_type=content_type, object_id=object_id)
                    print(">>> Finding the linked object, we got back: " + str(created))
                    print(ao)
                    self.instance.attached_objects.add(ao)
                    print("instance saved!")

