# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url

from cosinnus_conference import views

app_name = 'conference'

cosinnus_group_patterns = [
    url(r'^management/$', views.conference_management,
        name='management'),
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
    url(r'^workshop-participants-upload/$', views.workshop_participants_upload,
        name='workshop-participants-upload'),
    url(r'^workshop-participants-upload-skeleton/$',
        views.workshop_participants_upload_skeleton, name='workshop-participants-upload-skeleton'),
    url(r'^workshop-participants-download/$', views.workshop_participants_download,
        name='workshop-participants-download'),

    url(r'^$', views.conference_page,
        name='index'),
    url(r'^(?P<slug>[^/]+)/$', views.conference_page,
        name='room'),

]

cosinnus_root_patterns = [
]
urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
