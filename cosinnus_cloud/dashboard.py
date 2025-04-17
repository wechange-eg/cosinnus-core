# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django import forms
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from cosinnus.models.widget import WidgetConfig
from cosinnus.utils.dashboard import DashboardWidget, DashboardWidgetForm
from cosinnus.utils.urls import group_aware_reverse

logger = logging.getLogger('cosinnus')


class LatestCloudFilesForm(DashboardWidgetForm):
    amount = forms.IntegerField(label='Amount', initial=5, min_value=0, help_text='0 means unlimited', required=False)


class Latest(DashboardWidget):
    app_name = 'cloud'
    form_class = LatestCloudFilesForm
    model = None
    title = _('Latest Cloud files')
    user_model_attr = None  # No filtering on user page
    widget_name = 'latest'

    def get_data(self, offset=0):
        """Returns a tuple (data, rows_returned, has_more) of the rendered data and how many items were returned.
        if has_more == False, the receiving widget will assume no further data can be loaded.
        Disabled/Stubbed as the respective NextCloud API is not available anymore.
        """
        rows = []
        total_count = 0
        has_more = False
        had_error = False

        data = {
            'rows': rows,
            'had_error': had_error,
            'no_data': _('No cloud files yet'),
            'group': self.config.group,
            'total_count': total_count,
        }
        return (render_to_string('cosinnus_cloud/widgets/latest.html', data), len(rows), has_more)

    @property
    def title_url(self):
        if self.config.type == WidgetConfig.TYPE_MICROSITE:
            return ''
        if self.config.group:
            return group_aware_reverse('cosinnus:cloud:index', kwargs={'group': self.config.group})
        return ''
