# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url

from cosinnus.conf import settings
from cosinnus_conference import views

app_name = 'conference'

cosinnus_group_patterns = [
    url(r'^user-accounts/$', views.conference_temporary_users,
        name='temporary-users'),
    url(r'^room-management/$', views.conference_room_management,
        name='room-management'),
    url(r'^room-management/add/$', views.conference_room_add,
        name='room-add'),
    url(r'^room-management/edit/(?P<slug>[^/]+)/$',
        views.conference_room_edit, name='room-edit'),
    url(r'^room-management/delete/(?P<slug>[^/]+)/$',
        views.conference_room_delete, name='room-delete'),
    url(r'^maintenance/$', views.conference_page_maintenance,
        name='page-maintenance'),
    url(r'^maintenance/(?P<slug>[^/]+)/$',
        views.conference_page_maintenance, name='page-maintenance-room'),
    url(r'^participation-manangement/$', views.conference_participation_management,
        name='participation-management'),
    url(r'^participation-manangement/applications/$', views.conference_applications,
        name='participation-management-applications'),
    url(r'^workshop-participants-upload-skeleton/$',
        views.workshop_participants_upload_skeleton, name='workshop-participants-upload-skeleton'),
    url(r'^workshop-participants-download/$', views.workshop_participants_download,
        name='workshop-participants-download'),
    url(r'^participation-manangement/applicants-details-download/$', views.conference_applicant_details_download ,
        name='applicants-details-download'),
    url(r'^recorded_meetings/$', views.conference_recorded_meetings,
        name='recorded-meetings'),
    url(r'^recorded_meetings/delete/(?P<recording_id>[^/]+)/$', views.conference_recorded_meeting_delete,
        name='delete-recorded-meeting'),
    url(r'^reminders/$', views.conference_reminders,
        name='reminders'),
    url(r'^confirm_send_reminder/$', views.conference_confirm_send_reminder,
        name='confirm_send_reminder'),
    url(r'^apply/$', views.conference_application,
        name='application'),
    url(r'^$', views.conference_page,
        name='index'),
    url(r'^(?P<slug>[^/]+)/$', views.conference_page,
        name='room'),
    url(r'^(?P<slug>[^/]+)/#/(?P<event_id>[^/]+)$', views.conference_page,
        name='room-event'),
]

if settings.COSINNUS_CONFERENCE_STATISTICS_ENABLED:
    cosinnus_group_patterns = [
        url(r'^statistics/$', views.conference_statistics, name='statistics'),
        url(r'^statistics/download/$', views.conference_statistics_download, name='statistics-download'),
        url(r'^statistics/download/events/$', views.conference_event_statistics_download, name='event-statistics-download'),
        url(r'^statistics/download/users/$', views.conference_user_data_download, name='user-data-download'),
    ] + cosinnus_group_patterns

cosinnus_root_patterns = [
]
urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
