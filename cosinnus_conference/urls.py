# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import re_path

from cosinnus.conf import settings
from cosinnus_conference import views

app_name = 'conference'

cosinnus_group_patterns = [
    re_path(r'^user-accounts/$', views.conference_temporary_users, name='temporary-users'),
    re_path(r'^room-management/$', views.conference_room_management, name='room-management'),
    re_path(r'^room-management/add/$', views.conference_room_add, name='room-add'),
    re_path(r'^room-management/edit/(?P<slug>[^/]+)/$', views.conference_room_edit, name='room-edit'),
    re_path(r'^room-management/delete/(?P<slug>[^/]+)/$', views.conference_room_delete, name='room-delete'),
    re_path(r'^maintenance/$', views.conference_page_maintenance, name='page-maintenance'),
    re_path(r'^maintenance/(?P<slug>[^/]+)/$', views.conference_page_maintenance, name='page-maintenance-room'),
    re_path(r'^participation-management/$', views.conference_participation_management, name='participation-management'),
    re_path(
        r'^participation-management/applications/$',
        views.conference_applications,
        name='participation-management-applications',
    ),
    re_path(
        r'^workshop-participants-upload-skeleton/$',
        views.workshop_participants_upload_skeleton,
        name='workshop-participants-upload-skeleton',
    ),
    re_path(
        r'^workshop-participants-download/$',
        views.workshop_participants_download,
        name='workshop-participants-download',
    ),
    re_path(
        r'^participation-management/applicants-details-download/$',
        views.conference_applicant_details_download,
        name='applicants-details-download',
    ),
    re_path(r'^reminders/$', views.conference_reminders, name='reminders'),
    re_path(r'^confirm_send_reminder/$', views.conference_confirm_send_reminder, name='confirm_send_reminder'),
    re_path(r'^apply/$', views.conference_application, name='application'),
    re_path(r'^$', views.conference_page, name='index'),
    re_path(r'^(?P<slug>[^/]+)/$', views.conference_page, name='room'),
    re_path(r'^(?P<slug>[^/]+)/#/(?P<event_id>[^/]+)$', views.conference_page, name='room-event'),
]

if not settings.COSINNUS_CONFERENCES_USE_COMPACT_MODE:
    cosinnus_group_patterns = [
        re_path(r'^recorded_meetings/$', views.conference_recorded_meetings, name='recorded-meetings'),
        re_path(
            r'^recorded_meetings/delete/(?P<recording_id>[^/]+)/$',
            views.conference_recorded_meeting_delete,
            name='delete-recorded-meeting',
        ),
    ] + cosinnus_group_patterns


if not settings.COSINNUS_CONFERENCES_USE_COMPACT_MODE and settings.COSINNUS_CONFERENCE_STATISTICS_ENABLED:
    cosinnus_group_patterns = [
        re_path(r'^statistics/$', views.conference_statistics, name='statistics'),
        re_path(r'^statistics/download/$', views.conference_statistics_download, name='statistics-download'),
        re_path(
            r'^statistics/download/events/$',
            views.conference_event_statistics_download,
            name='event-statistics-download',
        ),
        re_path(r'^statistics/download/users/$', views.conference_user_data_download, name='user-data-download'),
    ] + cosinnus_group_patterns

cosinnus_root_patterns = []
urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
