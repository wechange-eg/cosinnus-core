# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from cosinnus.utils.dashboard import DashboardWidget, DashboardWidgetForm

from cosinnus_event.models import Event, upcoming_event_filter
from cosinnus.views.mixins.reflected_objects import MixReflectedObjectsMixin
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user

from cosinnus.conf import settings


class UpcomingEventsForm(DashboardWidgetForm):
    amount = forms.IntegerField(label="Amount", initial=5, min_value=0,
        help_text="0 means unlimited", required=False)
    template_name = 'cosinnus_event/widgets/event_widget_form.html'
    
    def __init__(self, *args, **kwargs):
        kwargs.pop('group', None)
        super(UpcomingEventsForm, self).__init__(*args, **kwargs)


class UpcomingEvents(MixReflectedObjectsMixin, DashboardWidget):

    app_name = 'event'
    form_class = UpcomingEventsForm
    model = Event
    title = _('Upcoming Events')
    user_model_attr = None  # No filtering on user page
    widget_name = 'upcoming'
    widget_template_name = 'cosinnus_event/widgets/event_widget.html'
    template_name = 'cosinnus_event/widgets/upcoming.html'
    
    def get_data(self, offset=0):
        """ Returns a tuple (data, rows_returned, has_more) of the rendered data and how many items were returned.
            if has_more == False, the receiving widget will assume no further data can be loaded.
         """
        count = int(self.config['amount'])
        all_events = self.get_queryset().select_related('group').all()
        calendar_events = all_events
        if not getattr(settings, 'COSINNUS_EVENT_CALENDAR_ALSO_SHOWS_PAST_EVENTS', False):
            calendar_events = upcoming_event_filter(all_events)
        events = upcoming_event_filter(all_events)
        
        if count != 0:
            events = events.all()[offset:offset+count]
        
        event_display = 'calendar'

        if getattr(settings, 'COSINNUS_CALENDAR_WIDGET_DISPLAY_AS_LIST', False):
            event_display = 'list'
        
        data = {
            'events': events,
            'event_display': event_display,
            'calendar_events': calendar_events,
            'no_data': _('No upcoming events'),
            'group': self.config.group,
        }
        return (render_to_string(self.template_name, data), len(events), len(events) >= count)

    def get_queryset(self):
        qs = super(UpcomingEvents, self).get_queryset()
        qs = filter_tagged_object_queryset_for_user(qs, self.request.user)
        return qs
