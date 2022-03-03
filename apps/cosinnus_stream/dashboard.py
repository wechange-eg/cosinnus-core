# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import defaultdict

from django import forms
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from cosinnus.utils.dashboard import DashboardWidget, DashboardWidgetForm
from cosinnus_stream.models import Stream
from django.urls import reverse
from django.core.exceptions import ImproperlyConfigured



class MyStreamsForm(DashboardWidgetForm):
    amount = forms.IntegerField(label="Amount", initial=15, min_value=0,
        help_text="0 means unlimited", required=False)
    

class MyStreamsWidget(DashboardWidget):

    app_name = 'stream'
    form_class = MyStreamsForm
    model = Stream
    title = _('My Streams')
    #user_model_attr = 'assigned_to'
    user_model_attr = 'creator'
    widget_name = 'my_streams'
    allow_on_user = True
    
    def get_queryset(self):
        if not self.model:
            raise ImproperlyConfigured('%s must define a model', self.__class__.__name__)
        qs = self.model._default_manager.filter(**self.get_queryset_filter())
        qs = qs.filter(is_my_stream__exact=False)
        return qs

    def get_data(self, offset=0):
        """ Returns a tuple (data, rows_returned, has_more) of the rendered data and how many items were returned.
            if has_more == False, the receiving widget will assume no further data can be loaded.
         """
        
        qs = self.get_queryset()
        
        data = {
            'user': self.request.user,
            'my_stream_unread': Stream.objects.my_stream_unread_count(self.request.user),
            'streams':qs,
        }
        return (render_to_string('cosinnus_stream/widgets/my_streams.html', data), 0, False)

    @property
    def title_url(self):
        return reverse('cosinnus:my_stream')
    
