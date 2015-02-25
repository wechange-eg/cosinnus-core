# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django import forms
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.forms.fields import ChoiceField
from cosinnus.utils.urls import group_aware_reverse


class DashboardWidgetForm(forms.Form):
    template_name = None
    
    # type form field needs to be here, but be hidden in the frontend
    type = forms.IntegerField(widget=forms.HiddenInput())
    # the sort field, arbitrary value field that is sorted on for widget order
    sort_field = forms.CharField(label=_("Sort_field"), help_text=_("Enter a number for sort order"), required=False)
    
    #default fields for all widgets
    widget_title = forms.CharField(label=_("Widget label"), help_text=_("Enter a title for the widget"), required=False)
    widget_icon = forms.CharField(label=_("Widget icon"), help_text=_("A font-awesome icon for the widget"), required=False)
    link_label = forms.CharField(label=_("Link label"), help_text=_("Enter a label for the widget-button"), required=False)
    
    

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


class EmptyWidgetForm(DashboardWidgetForm):
    template_name = 'cosinnus/widgets/empty_widget_form.html'
    
    def __init__(self, *args, **kwargs):
        kwargs.pop('group', None)
        super(EmptyWidgetForm, self).__init__(*args, **kwargs)
        

class InfoWidgetForm(DashboardWidgetForm):
    template_name = 'cosinnus/widgets/info_widget_form.html'
    
    text = forms.CharField(label=_("Text"), widget=forms.Textarea, help_text=_("Enter a description"), required=False)
    
    def __init__(self, *args, **kwargs):
        group = kwargs.pop('group', None)
        super(InfoWidgetForm, self).__init__(*args, **kwargs)
        
        from cosinnus.forms.attached_object import AttachableWidgetSelect2Field
        self.fields['images'] = AttachableWidgetSelect2Field(
            label=_("Attachments"), 
            help_text=_("Type the title and/or type of attachment"), 
            data_url=group_aware_reverse('cosinnus:attached_object_select2_view', kwargs={'group': group, 'model':'cosinnus_file.FileEntry'}) + '?model_as_target=1',
            required=False,
            initial = kwargs.get('initial', {}).pop('images', '')
        )
        
