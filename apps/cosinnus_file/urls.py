# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import url
from cosinnus_file import views

app_name = 'file'

cosinnus_root_patterns = []


cosinnus_group_patterns = [
    url(r'^list/$', views.file_hybrid_list_view, name='list'),
    url(r'^list/download/$', views.folder_download_view, name='download-folder'),
    url(r'^list/move_element/$', views.move_element_view, name='move-element'),
    url(r'^list/delete_element/$', views.delete_element_view, name='delete-element'),
    url(r'^list/(?P<slug>[^/]+)/$', views.file_hybrid_list_view, name='list'),
    url(r'^list/(?P<slug>[^/]+)/download/$', views.folder_download_view, name='download-folder'),
    url(r'^upload_inline/$', views.file_upload_inline, name='upload-inline'),
    url(r'^(?P<slug>[^/]+)/$', views.file_update_view, name='edit'),

    #url(r'^list/(?P<tag>[^/]+)/$', views.file_list_view', name='list-filtered'),
    #url(r'^(?P<slug>[^/]+)/$', views.file_detail_view', name='file'),
    url(r'^(?P<slug>[^/]+)/download$', views.file_download_view, name='download'),
    url(r'^(?P<slug>[^/]+)/download/(?P<pretty_filename>[^/]+)$', views.file_download_view, name='pretty-download'),
    url(r'^(?P<slug>[^/]+)/save', views.file_download_view, {'force_download': True}, name='save'),
    url(r'^(?P<slug>[^/]+)/delete/$', views.file_delete_view, {'form_view': 'delete'}, name='delete'),
    
    url(r'^$', views.file_index_view, name='index'),
]

if settings.COSINNUS_ROCKET_EXPORT_ENABLED:
    cosinnus_group_patterns += [
        url(r'^(?P<slug>[^/]+)/rocket$', views.rocket_file_download_view, name='rocket-download'),
    ]

urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
