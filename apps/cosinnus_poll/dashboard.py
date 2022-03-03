# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from cosinnus.utils.dashboard import DashboardWidget, DashboardWidgetForm

from cosinnus_poll.models import Poll, current_poll_filter


class CurrentPollsForm(DashboardWidgetForm):
    amount = forms.IntegerField(label="Amount", initial=5, min_value=0,
        help_text="0 means unlimited", required=False)
    template_name = 'cosinnus_poll/widgets/poll_widget_form.html'
    
    def __init__(self, *args, **kwargs):
        kwargs.pop('group', None)
        super(CurrentPollsForm, self).__init__(*args, **kwargs)


class CurrentPolls(DashboardWidget):

    app_name = 'poll'
    form_class = CurrentPollsForm
    model = Poll
    title = _('Current Polls')
    user_model_attr = None  # No filtering on user page
    widget_name = 'current'
    template_name = 'cosinnus_poll/widgets/current.html'
    
    def get_data(self, offset=0):
        """ Returns a tuple (data, rows_returned, has_more) of the rendered data and how many items were returned.
            if has_more == False, the receiving widget will assume no further data can be loaded.
         """
        count = int(self.config['amount'])
        all_current_polls = self.get_queryset().\
                filter(state__lt=Poll.STATE_ARCHIVED).\
                order_by('-created').\
                select_related('group').all()
        polls = all_current_polls
        
        if count != 0:
            polls = polls.all()[offset:offset+count]
        
        data = {
            'polls': polls,
            'all_current_polls': all_current_polls,
            'no_data': _('No current polls'),
            'group': self.config.group,
        }
        return (render_to_string(self.template_name, data), len(polls), len(polls) >= count)

    def get_queryset(self):
        qs = super(CurrentPolls, self).get_queryset()
        return current_poll_filter(qs)
