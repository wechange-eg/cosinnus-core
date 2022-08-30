# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings  # noqa
from appconf import AppConf


class CosinnusEventConf(AppConf):
    # identifier for token label used for the event-feed token in cosinnus_profile.settings 
    TOKEN_EVENT_FEED = 'event_feed'
    
    # should the calendar view load *all* events, even past ones? 
    # can be very DB intensive for groups with many events
    CALENDAR_ALSO_SHOWS_PAST_EVENTS = True
    
    # if True, and a group slug is set for NEWW_EVENTS_GROUP_SLUG, 
    # that group will also show all other group/project's public events in its calendar
    EVENTS_GROUP_SHOWS_ALL_PUBLIC_EVENTS = False
    
    