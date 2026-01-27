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
    DIFFERENTIATE_ONLINE_AND_ONSITE_EVENTS = False

    # Hide event list filters (e.g. 'o', 'creator', see EventFilter class).
    EVENT_LIST_HIDDEN_FILTERS = []

    # Enable v3 calendar, replacing v2 event pages.
    V3_CALENDAR_ENABLED = False
