# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django import forms
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.forms.fields import ChoiceField


class DashboardWidgetForm(forms.Form):
    template_name = None
    
    type = forms.IntegerField()

    def clean(self):
        cleaned_data = super(DashboardWidgetForm, self).clean()
        for key, value in six.iteritems(cleaned_data):
            if value is None:
                # We need to find a default value: The approach we are using
                # here is to first take the initial value from the form and if
                # this is not defined, take the initial value directly from the
                # field. If the field has no initial value, fall back to an
                # empty string
                if key in self.initial:
                    value = self.initial[key]
                elif self.fields[key].initial:
                    value = self.fields[key].initial
            if value is None:
                value = ''
            cleaned_data[key] = value
        return cleaned_data



class InfoWidgetForm(DashboardWidgetForm):
    template_name = 'cosinnus/widgets/info_widget_form.html'
    
    text = forms.CharField(label="Text", widget=forms.Textarea, help_text="Enter a description", required=False)
    image = ChoiceField(
            label=_("Attachments"), 
            help_text=_("fake"), 
            required=False
        )
    
    
    def __init__(self, *args, **kwargs):
        group = kwargs.pop('group', None)
        
        super(InfoWidgetForm, self).__init__(*args, **kwargs)
        """
        # retrieve the attached objects ids to select them in the update view
        preresults = []
        if self.instance and self.instance.pk:
            for attached in self.instance.attached_objects.all():
                if attached and attached.target_object:
                    obj = attached.target_object
                    text_only = (attached.model_name+":"+str(obj.id), "%s" % (obj.title),)
                    #text_only = (attached.model_name+":"+str(obj.id), "&lt;i&gt;%s&lt;/i&gt; %s" % (attached.model_name, obj.title),)  
                    # TODO: sascha: returning unescaped html here breaks the javascript of django-select2
                    html = build_attachment_field_result(attached.model_name, obj) 
                    preresults.append(text_only)
                    
        # add a field for each model type of attachable file provided by cosinnus apps
        # each field's name is something like 'attached:cosinnus_file.FileEntry'
        # and fill the field with all available objects for that type (this is passed from our view)
        source_model_id = self._meta.model._meta.app_label + '.' + self._meta.model._meta.object_name
        """
        """ Add attachable objects field if this model is configured in settings.py to have objects that can be attached to it """
        from cosinnus.forms.attached_object import AttachableObjectSelect2MultipleChoiceField
        
        self.fields['image'] = AttachableObjectSelect2MultipleChoiceField(
            label=_("Attachments"), 
            help_text=_("Type the title and/or type of attachment"), 
            data_url=reverse('cosinnus:attached_object_select2_view', kwargs={'group': group.slug, 'model':'cosinnus_file.FileEntry'}) + '?model_is_target=1',
            required=False
        )
        
        # we need to cheat our way around select2's annoying way of clearing initial data fields
        self.fields['image'].choices = ()#preresults #((1, 'hi'),)
        self.fields['image'].initial = []#[key for key,val in preresults] #[1]
        