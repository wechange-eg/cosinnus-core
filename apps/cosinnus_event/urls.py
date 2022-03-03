# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus_event import views
from django.conf.urls import url


app_name = 'event'

cosinnus_group_patterns = [
    url(r'^$', views.index_view, name='index'),
    url(r'^calendar/$', views.list_view, name='list'),
    url(r'^calendar/(?P<tag>[^/]+)/$', views.list_view, name='list-filtered'),
    # deprecated URL, see 'team-feed' for the new URL. left as backwards compatibility for old ical imports. 
    url(r'^feed/$', views.event_ical_feed, name='feed'),
    # deprecated URL, see 'team-feed-entry' for the new URL. left as backwards compatibility for old ical imports. 
    url(r'^feed/(?P<slug>[^/]+)/$', views.event_ical_feed_single, name='feed-entry'),

    url(r'^doodle/list/$', views.doodle_list_view,  name='doodle-list'),
    url(r'^doodle/add/$', views.doodle_add_view, {'form_view': 'add'}, name='doodle-add'),
    url(r'^doodle/(?P<slug>[^/]+)/$', views.doodle_vote_view, {'form_view': 'vote'}, name='doodle-vote'),
    url(r'^doodle/(?P<slug>[^/]+)/archived/$', views.doodle_vote_view, {'form_view': 'archived'}, name='doodle-archived'),
    url(r'^doodle/(?P<slug>[^/]+)/edit/$', views.doodle_edit_view, {'form_view': 'edit'}, name='doodle-edit'),
    url(r'^doodle/(?P<slug>[^/]+)/delete/$', views.doodle_delete_view, {'form_view': 'delete'}, name='doodle-delete'),
    url(r'^doodle/(?P<slug>[^/]+)/complete/(?P<suggestion_id>\d+)/$', views.doodle_complete_view, name='doodle-complete'),

    url(r'^list/$', views.detailed_list_view, name='list_detailed'),
    url(r'^list/past/$', views.past_events_list_view, name='list_past'),
    url(r'^list/archived/$', views.archived_doodles_list_view, name='doodle-list-archived'),
    url(r'^list/conferences/$', views.conference_list_view, name='list_conferences'),
    url(r'^list/conference-events/$', views.conference_event_list_view, name='conference-event-list'),
    url(r'^list/delete_element/$', views.delete_element_view, name='delete-element'),
    url(r'^add/$', views.entry_add_view,  {'form_view': 'add'},  name='event-add'),
    
    url(r'^conference/(?P<room_slug>[^/]+)/add/$', views.conference_event_add_view, {'form_view': 'add'}, name='conference-event-add'),
    url(r'^conference/(?P<room_slug>[^/]+)/edit/(?P<slug>[^/]+)/$', views.conference_event_edit_view, {'form_view': 'edit'}, name='conference-event-edit'),
    url(r'^conference/(?P<room_slug>[^/]+)/delete/(?P<slug>[^/]+)/$', views.conference_event_delete_view, {'form_view': 'delete'}, name='conference-event-delete'),
    # deprecated URL, see 'team-conference-event-entry' for the new URL. left as backwards compatibility for old ical imports. 
    url(r'^conference/feed/(?P<slug>[^/]+)/$', views.conference_event_ical_feed_single, name='conference-event-entry'),

    url(r'^(?P<slug>[^/]+)/$', views.entry_detail_view, {'form_view': 'edit'},  name='event-detail'),
    url(r'^(?P<slug>[^/]+)/edit/$', views.entry_edit_view, {'form_view': 'edit'}, name='event-edit'),
    url(r'^(?P<slug>[^/]+)/delete/$', views.entry_delete_view, {'form_view': 'delete'}, name='event-delete'),
    url(r'^(?P<slug>[^/]+)/assign_attendance/$', views.assign_attendance_view, name='event-assign-attendance'),
    
    url(r'^(?P<event_slug>[^/]+)/comment/$', views.comment_create, name='comment'),
    url(r'^comment/(?P<pk>\d+)/$', views.comment_detail, name='comment-detail'),
    url(r'^comment/(?P<pk>\d+)/delete/$', views.comment_delete, name='comment-delete'),
    url(r'^comment/(?P<pk>\d+)/update/$', views.comment_update, name='comment-update'),
]


cosinnus_root_patterns = [
    url(r'^events/team/(?P<team_id>\d+)/feed/$', views.team_event_ical_feed, name='team-feed'),
    url(r'^events/team/(?P<team_id>\d+)/feed/(?P<slug>[^/]+)/$', views.team_event_ical_feed_single, name='team-feed-entry'),
    url(r'^events/team/(?P<team_id>\d+)/conference/feed/(?P<slug>[^/]+)/$', views.team_conference_event_ical_feed_single, name='team-conference-event-entry'),
    url(r'^events/feed/all/$', views.event_ical_feed_global, name='feed-global'),
    url(r'^events/(?P<pk>\d+)/update', views.event_api_update, name='event_api_update')
]
urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns

