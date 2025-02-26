# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from appconf import AppConf
from django.conf import settings  # noqa


class CosinnusEventConf(AppConf):
    # identifier for token label used for the event-feed token in cosinnus_profile.settings
    TOKEN_EVENT_FEED = 'event_feed'

    # the number of days in the past that past events in iCal feeds are included
    ICAL_FEED_SHOW_PAST_DAYS = 90

    # should the calendar view load *all* events, even past ones?
    # can be very DB intensive for groups with many events
    CALENDAR_ALSO_SHOWS_PAST_EVENTS = True

    # if True, and a group slug is set for NEWW_EVENTS_GROUP_SLUG,
    # that group will also show all other group/project's public events in its calendar
    EVENTS_GROUP_SHOWS_ALL_PUBLIC_EVENTS = False

    # Differentiate online vs on-site events. Online events have no location set, on-site events have one set.
    # Adds a hint to the locations field in event and compact mode conference forms and to the compact mode conference
    # microsite.
    # Note: Make sure to remove the "online_or_onsite" filter from the EVENT_LIST_HIDDEN_FILTERS settings if enabled.
    DIFFERENTIATE_ONLINE_AND_ONSITE_EVENTS = False

    # Hide event list filters (e.g. 'o', 'creator', see EventFilter class).
    # The online/on-site filter is hidden per default.
    EVENT_LIST_HIDDEN_FILTERS = ['online_or_onsite']
