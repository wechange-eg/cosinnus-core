# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url
from cosinnus_note import views

app_name = 'note'

cosinnus_root_patterns = [ 
    url(r'^notes/embed/all/$', views.note_embed_global, name='embed-global'),
    url(r'^notes/embed/$', views.note_embed_current_portal, name='embed-current-portal'),
]
    
cosinnus_group_patterns = [
    url(r'^$', views.note_index, name='index'),
    url(r'^list/$', views.note_list, name='list'),
    url(r'^embed/$', views.note_embed, name='embed'),
    url(r'^add/$', views.note_create, name='add'),
    url(r'^(?P<slug>[^/]+)/$', views.note_detail, name='note'),
    url(r'^(?P<slug>[^/]+)/delete/$', views.note_delete, name='delete'),
    url(r'^(?P<slug>[^/]+)/update/$', views.note_update, name='update'),
    url(r'^(?P<note_slug>[^/]+)/comment/$', views.comment_create, name='comment'),
    url(r'^comment/(?P<pk>\d+)/$', views.comment_detail, name='comment-detail'),
    url(r'^comment/(?P<pk>\d+)/delete/$', views.comment_delete, name='comment-delete'),
    url(r'^comment/(?P<pk>\d+)/update/$', views.comment_update, name='comment-update'),
]

urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
