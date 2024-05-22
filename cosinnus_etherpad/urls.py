# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import re_path

from cosinnus_etherpad import views

app_name = 'etherpad'

cosinnus_group_patterns = [
    re_path(r'^$', views.index_view, name='index'),
    re_path(r'^list/$', views.pad_hybrid_list_view, name='list'),
    re_path(r'^list/move_element/$', views.move_element_view, name='move-element'),
    re_path(r'^list/delete_element/$', views.delete_element_view, name='delete-element'),
    re_path(r'^list/(?P<slug>[^/]+)/$', views.pad_hybrid_list_view, name='list'),
    re_path(r'^(?P<slug>[^/]+)/edit/$', views.pad_write_view, name='pad-write'),
    re_path(r'^(?P<slug>[^/]+)/settings/$', views.pad_edit_view, name='pad-edit'),
    re_path(r'^(?P<slug>[^/]+)/$', views.pad_detail_view, name='pad-detail'),
    re_path(r'^(?P<slug>[^/]+)/csv/$', views.calc_csv_view, name='calc-csv'),
    re_path(r'^(?P<slug>[^/]+)/xlsx/$', views.calc_xlsx_view, name='calc-xlsx'),
    # re_path(r'^add-container/$', container_add_view', name='container-add'),
    re_path(r'^(?P<slug>[^/]+)/delete/$', views.pad_delete_view, name='pad-delete'),
    re_path(r'^(?P<slug>[^/]+)/archive/document/$', views.pad_archive_document, name='pad-archive-document'),
    re_path(r'^(?P<slug>[^/]+)/archive/file/$', views.pad_archive_file, name='pad-archive-file'),
    # re_path(r'^(?P<slug>[^/]+)/add-container/$',
    #    'container_add_view', name='container-add'),
]


cosinnus_root_patterns = []
urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
