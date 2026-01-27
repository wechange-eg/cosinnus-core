# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import path, re_path

from cosinnus.conf import settings
from cosinnus_event import views
from cosinnus_event.calendar import views as calendar_views

app_name = 'event'


cosinnus_group_patterns = []

if settings.COSINNUS_EVENT_V3_CALENDAR_ENABLED:
    # TODO: this is temporary, where the v3 calendar is included needs to be discussed.
    cosinnus_group_patterns += [
        re_path(r'^v3-calendar/$', calendar_views.calendar_view, name='calendar'),
    ]

# TODO: disable old views if the calendar is enabled, discuss which are replaced
cosinnus_group_patterns += [
    re_path(r'^$', views.index_view, name='index-redirect'),
    re_path(r'^calendar/$', views.list_view, name='index'),
    re_path(r'^calendar/$', views.list_view, name='list'),
    re_path(r'^calendar/(?P<tag>[^/]+)/$', views.list_view, name='list-filtered'),
    # deprecated URL, see 'team-feed' for the new URL. left as backwards compatibility for old ical imports.
    re_path(r'^feed/$', views.event_ical_feed, name='feed'),
    # deprecated URL, see 'team-feed-entry' for the new URL. left as backwards compatibility for old ical imports.
    re_path(r'^feed/(?P<slug>[^/]+)/$', views.event_ical_feed_single, name='feed-entry'),
    re_path(r'^poll/list/$', views.doodle_list_view, name='doodle-list'),
    re_path(r'^poll/add/$', views.doodle_add_view, {'form_view': 'add'}, name='doodle-add'),
    re_path(r'^poll/(?P<slug>[^/]+)/$', views.doodle_vote_view, {'form_view': 'vote'}, name='doodle-vote'),
    re_path(
        r'^poll/(?P<slug>[^/]+)/archived/$', views.doodle_vote_view, {'form_view': 'archived'}, name='doodle-archived'
    ),
    re_path(r'^poll/(?P<slug>[^/]+)/edit/$', views.doodle_edit_view, {'form_view': 'edit'}, name='doodle-edit'),
    re_path(r'^poll/(?P<slug>[^/]+)/delete/$', views.doodle_delete_view, {'form_view': 'delete'}, name='doodle-delete'),
    re_path(
        r'^poll/(?P<slug>[^/]+)/complete/(?P<suggestion_id>\d+)/$', views.doodle_complete_view, name='doodle-complete'
    ),
    # deprecated URLs, redirecting to poll/
    re_path(
        r'^doodle/list/$',
        views.doodle_poll_redirect_view,
        {'event_url_name': 'doodle-list'},
        name='doodle-poll-redirect-list',
    ),
    re_path(
        r'^doodle/add/$',
        views.doodle_poll_redirect_view,
        {'event_url_name': 'doodle-add'},
        name='doodle-poll-redirect-add',
    ),
    re_path(
        r'^doodle/(?P<slug>[^/]+)/$',
        views.doodle_poll_redirect_view,
        {'event_url_name': 'doodle-vote'},
        name='doodle-poll-redirect-vote',
    ),
    re_path(
        r'^doodle/(?P<slug>[^/]+)/archived/$',
        views.doodle_poll_redirect_view,
        {'event_url_name': 'doodle-archived'},
        name='doodle-poll-redirect-archived',
    ),
    re_path(
        r'^doodle/(?P<slug>[^/]+)/edit/$',
        views.doodle_poll_redirect_view,
        {'event_url_name': 'doodle-edit'},
        name='doodle-poll-redirect-edit',
    ),
    re_path(
        r'^doodle/(?P<slug>[^/]+)/delete/$',
        views.doodle_poll_redirect_view,
        {'event_url_name': 'doodle-delete'},
        name='doodle-poll-redirect-delete',
    ),
    re_path(
        r'^doodle/(?P<slug>[^/]+)/complete/(?P<suggestion_id>\d+)/$',
        views.doodle_poll_redirect_view,
        {'event_url_name': 'doodle-complete'},
        name='doodle-poll-redirect-complete',
    ),
    re_path(r'^list/$', views.detailed_list_view, name='list_detailed'),
    re_path(r'^list/past/$', views.past_events_list_view, name='list_past'),
    re_path(r'^list/archived/$', views.archived_doodles_list_view, name='doodle-list-archived'),
    re_path(r'^list/conferences/$', views.conference_list_view, name='list_conferences'),
    re_path(r'^list/conference-events/$', views.conference_event_list_view, name='conference-event-list'),
    re_path(r'^list/delete_element/$', views.delete_element_view, name='delete-element'),
    re_path(r'^add/$', views.entry_add_view, {'form_view': 'add'}, name='event-add'),
    re_path(
        r'^conference/(?P<room_slug>[^/]+)/add/$',
        views.conference_event_add_view,
        {'form_view': 'add'},
        name='conference-event-add',
    ),
    re_path(
        r'^conference/(?P<room_slug>[^/]+)/edit/(?P<slug>[^/]+)/$',
        views.conference_event_edit_view,
        {'form_view': 'edit'},
        name='conference-event-edit',
    ),
    re_path(
        r'^conference/(?P<room_slug>[^/]+)/delete/(?P<slug>[^/]+)/$',
        views.conference_event_delete_view,
        {'form_view': 'delete'},
        name='conference-event-delete',
    ),
    # deprecated URL, see 'team-conference-event-entry' for the new URL. left as backwards compatibility for old ical
    # imports.
    re_path(
        r'^conference/feed/(?P<slug>[^/]+)/$', views.conference_event_ical_feed_single, name='conference-event-entry'
    ),
    re_path(r'^(?P<slug>[^/]+)/$', views.entry_detail_view, {'form_view': 'edit'}, name='event-detail'),
    re_path(r'^(?P<slug>[^/]+)/edit/$', views.entry_edit_view, {'form_view': 'edit'}, name='event-edit'),
    re_path(r'^(?P<slug>[^/]+)/delete/$', views.entry_delete_view, {'form_view': 'delete'}, name='event-delete'),
    re_path(r'^(?P<slug>[^/]+)/assign_attendance/$', views.assign_attendance_view, name='event-assign-attendance'),
    re_path(r'^(?P<event_slug>[^/]+)/comment/$', views.comment_create, name='comment'),
    re_path(r'^comment/(?P<pk>\d+)/$', views.comment_detail, name='comment-detail'),
    re_path(r'^comment/(?P<pk>\d+)/delete/$', views.comment_delete, name='comment-delete'),
    re_path(r'^comment/(?P<pk>\d+)/update/$', views.comment_update, name='comment-update'),
]


cosinnus_root_patterns = [
    path('events/team/<int:team_id>/feed/', views.team_event_ical_feed, name='team-feed'),
    path('events/team/<int:team_id>/feed/<slug:slug>/', views.team_event_ical_feed_single, name='team-feed-entry'),
    path(
        'events/team/<int:team_id>/conference/feed/<slug:slug>/',
        views.team_conference_event_ical_feed_single,
        name='team-conference-event-entry',
    ),
    path('events/feed/all/', views.event_ical_feed_global, name='feed-global'),
    path('events/<int:pk>/update', views.event_api_update, name='event_api_update'),
]

urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
