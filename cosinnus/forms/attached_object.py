# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django import forms

class FormAttachable(forms.ModelForm):
    
    def __init__(self, *args, **kwargs):
        attached_sets = kwargs.pop('attached_files_querysets', None) 
        super(FormAttachable, self).__init__(*args, **kwargs)
        
        print(">>> query_sets passed forward:")
        print(attached_sets)
        
        for model_name, queryset in attached_sets.items():
            self.fields[model_name] = forms.ModelMultipleChoiceField(queryset=queryset, required=False)#,label='FFFFFUUUU')
    
    def save(self, *args, **kwargs):
        instance = super(FormAttachable, self).save(*args, **kwargs)
        
        print (">>> Now in the save func: instance is:")
        print(instance)
        print (">>> cleaned data")
        print(self.cleaned_data)
        
        """ TODO: save attached_objects to instance """
        
        
        return instance
        