# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from cosinnus.models.widget import WidgetConfig
from cosinnus.utils.dashboard import DashboardWidget, DashboardWidgetForm
from cosinnus.utils.urls import group_aware_reverse
from cosinnus_etherpad.models import Etherpad


class LatestEtherpadsForm(DashboardWidgetForm):
    amount = forms.IntegerField(label='Amount', initial=5, min_value=0, help_text='0 means unlimited', required=False)


class Latest(DashboardWidget):
    app_name = 'etherpad'
    form_class = LatestEtherpadsForm
    model = Etherpad
    title = _('Last accessed Etherpads')
    user_model_attr = None  # No filtering on user page
    widget_name = 'latest'

    def get_data(self, offset=0):
        """Returns a tuple (data, rows_returned, has_more) of the rendered data and how many items were returned.
        if has_more == False, the receiving widget will assume no further data can be loaded.
        """
        count = int(self.config['amount'])
        qs = (
            self.get_queryset()
            .select_related('group')
            .order_by('-last_accessed', '-created')
            .filter(is_container=False)
        )
        if count != 0:
            qs = qs[offset : offset + count]

        data = {
            'rows': qs,
            'no_data': _('No etherpads'),
            'group': self.config.group,
        }
        return (render_to_string('cosinnus_etherpad/widgets/latest.html', data), len(qs), len(qs) >= count)

    @property
    def title_url(self):
        if self.config.type == WidgetConfig.TYPE_MICROSITE:
            return ''
        if self.config.group:
            return group_aware_reverse('cosinnus:etherpad:list', kwargs={'group': self.config.group}) + '?o=-created'
        return ''
