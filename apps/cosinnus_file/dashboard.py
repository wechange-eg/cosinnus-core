# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from cosinnus.utils.dashboard import DashboardWidget, DashboardWidgetForm

from cosinnus_file.models import FileEntry
from cosinnus.models.widget import WidgetConfig
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.utils.filters import exclude_special_folders


class LatestFileEntryForm(DashboardWidgetForm):
    amount = forms.IntegerField(label="Amount", initial=5, min_value=0,
        help_text="0 means unlimited", required=False)
    template_name = 'cosinnus_file/widgets/file_widget_form.html'
    
    def __init__(self, *args, **kwargs):
        kwargs.pop('group', None)
        super(LatestFileEntryForm, self).__init__(*args, **kwargs)

class Latest(DashboardWidget):

    app_name = 'file'
    form_class = LatestFileEntryForm
    model = FileEntry
    title = _('Latest Files')
    user_model_attr = None  # No filtering on user page
    widget_name = 'latest'

    def get_data(self, offset=0):
        """ Returns a tuple (data, rows_returned, has_more) of the rendered data and how many items were returned.
            if has_more == False, the receiving widget will assume no further data can be loaded.
         """
        count = int(self.config['amount'])
        qs = self.get_queryset().select_related('group').order_by('-created').all()
        qs = exclude_special_folders(qs)
        if count != 0:
            qs = qs[offset:offset+count]
            
        data = {
            'rows': qs,
            'no_data': _('No files'),
        }
        return (render_to_string('cosinnus_file/widgets/latest.html', data), len(qs), len(qs) >= count)

    def get_queryset(self):
        qs = super(Latest, self).get_queryset()
        return qs.filter(is_container=False)
    
    @property
    def title_url(self):
        if self.config.type == WidgetConfig.TYPE_MICROSITE:
            return ''
        if self.config.group:
            return group_aware_reverse('cosinnus:file:list', kwargs={'group': self.config.group}) + '?o=-created'
        return ''
