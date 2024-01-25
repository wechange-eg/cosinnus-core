# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import re_path, path
from cosinnus_note import views

app_name = 'note'

cosinnus_root_patterns = [ 
    path('notes/embed/all/', views.note_embed_global, name='embed-global'),
    path('notes/embed/', views.note_embed_current_portal, name='embed-current-portal'),
]
    
cosinnus_group_patterns = [
    re_path(r'^$', views.note_index, name='index'),
    re_path(r'^list/$', views.note_list, name='list'),
    re_path(r'^embed/$', views.note_embed, name='embed'),
    re_path(r'^add/$', views.note_create, name='add'),
    re_path(r'^(?P<slug>[^/]+)/$', views.note_detail, name='note'),
    re_path(r'^(?P<slug>[^/]+)/delete/$', views.note_delete, name='delete'),
    re_path(r'^(?P<slug>[^/]+)/update/$', views.note_update, name='update'),
    re_path(r'^(?P<note_slug>[^/]+)/comment/$', views.comment_create, name='comment'),
    re_path(r'^comment/(?P<pk>\d+)/$', views.comment_detail, name='comment-detail'),
    re_path(r'^comment/(?P<pk>\d+)/delete/$', views.comment_delete, name='comment-delete'),
    re_path(r'^comment/(?P<pk>\d+)/update/$', views.comment_update, name='comment-update'),
]

urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
