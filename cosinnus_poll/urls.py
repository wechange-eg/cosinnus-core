# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import re_path

from cosinnus_poll import views

app_name = 'poll'

cosinnus_group_patterns = [
    re_path(r'^$', views.index_view, name='index-redirect'),
    re_path(r'^list/$', views.poll_list_view, name='index', kwargs={'poll_view': 'current'}),
    re_path(r'^list/$', views.poll_list_view, name='list', kwargs={'poll_view': 'current'}),
    re_path(r'^list/past/$', views.poll_list_view, name='list_past', kwargs={'poll_view': 'past'}),
    re_path(r'^list/delete_element/$', views.delete_element_view, name='delete-element'),
    re_path(r'^add/$', views.poll_add_view, {'form_view': 'add'}, name='add'),
    re_path(r'^(?P<slug>[^/]+)/$', views.poll_vote_view, {'form_view': 'edit'}, name='detail'),
    re_path(r'^(?P<slug>[^/]+)/edit/$', views.poll_edit_view, {'form_view': 'edit'}, name='edit'),
    re_path(r'^(?P<slug>[^/]+)/delete/$', views.poll_delete_view, {'form_view': 'delete'}, name='delete'),
    re_path(r'^(?P<slug>[^/]+)/complete/$', views.poll_complete_view, name='complete', kwargs={'mode': 'complete'}),
    re_path(
        r'^(?P<slug>[^/]+)/complete/(?P<option_id>\d+)/$',
        views.poll_complete_view,
        name='complete',
        kwargs={'mode': 'complete'},
    ),
    re_path(r'^(?P<slug>[^/]+)/reopen/$', views.poll_complete_view, name='reopen', kwargs={'mode': 'reopen'}),
    re_path(r'^(?P<slug>[^/]+)/archive/$', views.poll_complete_view, name='archive', kwargs={'mode': 'archive'}),
    re_path(r'^(?P<poll_slug>[^/]+)/comment/$', views.comment_create, name='comment'),
    re_path(r'^comment/(?P<pk>\d+)/$', views.comment_detail, name='comment-detail'),
    re_path(r'^comment/(?P<pk>\d+)/delete/$', views.comment_delete, name='comment-delete'),
    re_path(r'^comment/(?P<pk>\d+)/update/$', views.comment_update, name='comment-update'),
]

cosinnus_root_patterns = []


urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
