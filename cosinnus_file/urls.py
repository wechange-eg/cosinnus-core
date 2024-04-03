# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.urls import re_path
from cosinnus_file import views

app_name = 'file'

cosinnus_root_patterns = []


cosinnus_group_patterns = [
    re_path(r'^list/$', views.file_hybrid_list_view, name='list'),
    re_path(r'^list/download/$', views.folder_download_view, name='download-folder'),
    re_path(r'^list/move_element/$', views.move_element_view, name='move-element'),
    re_path(r'^list/delete_element/$', views.delete_element_view, name='delete-element'),
    re_path(r'^list/(?P<slug>[^/]+)/$', views.file_hybrid_list_view, name='list'),
    re_path(r'^list/(?P<slug>[^/]+)/download/$', views.folder_download_view, name='download-folder'),
    re_path(r'^upload_inline/$', views.file_upload_inline, name='upload-inline'),
    re_path(r'^(?P<slug>[^/]+)/$', views.file_update_view, name='edit'),

    #re_path(r'^list/(?P<tag>[^/]+)/$', views.file_list_view', name='list-filtered'),
    #re_path(r'^(?P<slug>[^/]+)/$', views.file_detail_view', name='file'),
    re_path(r'^(?P<slug>[^/]+)/download$', views.file_download_view, name='download'),
    re_path(r'^(?P<slug>[^/]+)/download/(?P<pretty_filename>[^/]+)$', views.file_download_view, name='pretty-download'),
    re_path(r'^(?P<slug>[^/]+)/save', views.file_download_view, {'force_download': True}, name='save'),
    re_path(r'^(?P<slug>[^/]+)/delete/$', views.file_delete_view, {'form_view': 'delete'}, name='delete'),
    
    re_path(r'^$', views.file_index_view, name='index'),
]

if settings.COSINNUS_ROCKET_EXPORT_ENABLED:
    cosinnus_group_patterns += [
        re_path(r'^(?P<slug>[^/]+)/rocket$', views.rocket_file_download_view, name='rocket-download'),
    ]

urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
