# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url
from cosinnus_etherpad import views 

app_name = 'etherpad'

cosinnus_group_patterns = [
    url(r'^$', views.index_view, name='index'),
    url(r'^list/$', views.pad_hybrid_list_view, name='list'),
    url(r'^list/move_element/$', views.move_element_view, name='move-element'),
    url(r'^list/delete_element/$', views.delete_element_view, name='delete-element'),
    url(r'^list/(?P<slug>[^/]+)/$', views.pad_hybrid_list_view, name='list'),
    url(r'^(?P<slug>[^/]+)/edit/$', views.pad_write_view, name='pad-write'),
    url(r'^(?P<slug>[^/]+)/settings/$', views.pad_edit_view, name='pad-edit'),
    url(r'^(?P<slug>[^/]+)/$', views.pad_detail_view, name='pad-detail'),
    url(r'^(?P<slug>[^/]+)/csv/$', views.calc_csv_view, name='calc-csv'),
    url(r'^(?P<slug>[^/]+)/xlsx/$', views.calc_xlsx_view, name='calc-xlsx'),
    
    #url(r'^add-container/$', container_add_view', name='container-add'),
    url(r'^(?P<slug>[^/]+)/delete/$', views.pad_delete_view, name='pad-delete'),
    url(r'^(?P<slug>[^/]+)/archive/document/$', views.pad_archive_document, name='pad-archive-document'),
    url(r'^(?P<slug>[^/]+)/archive/file/$', views.pad_archive_file, name='pad-archive-file'),
    #url(r'^(?P<slug>[^/]+)/add-container/$',
    #    'container_add_view', name='container-add'),
]


cosinnus_root_patterns = []
urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
