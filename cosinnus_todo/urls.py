# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import re_path

from cosinnus.utils.url_patterns import api_patterns
from cosinnus_todo import views

app_name = 'todo'

cosinnus_group_patterns = [
    re_path(r'^$', views.index_view, name='index-redirect'),
    re_path(r'^list/$', views.todo_list_create_view, name='index'),
    re_path(r'^list/$', views.todo_list_create_view, name='list'),
    re_path(r'^list/move_element/$', views.move_element_view, name='move-element'),
    re_path(r'^list/(?P<listslug>[^/]+)/$', views.todo_list_create_view, name='list-list'),
    re_path(
        r'^list/(?P<listslug>[^/]+)/show/(?P<todoslug>[^/]+)/$', views.todo_list_create_view, name='todo-in-list-list'
    ),
    re_path(r'^delete/list/(?P<slug>[^/]+)/$', views.todolist_delete_view, name='todolist-delete'),
    re_path(r'^list/(?P<listslug>[^/]+)/add/$', views.entry_add_view, name='entry-add'),
    re_path(r'^todolist/list/$', views.todolist_list_view, name='todolist-list'),
    re_path(r'^todolist/add/$', views.todolist_add_view, name='todolist-add'),
    re_path(r'^(?P<slug>[^/]+)/$', views.entry_detail_view, name='entry-detail'),
    re_path(r'^(?P<slug>[^/]+)/edit/$', views.entry_edit_view, name='entry-edit'),
    re_path(r'^(?P<slug>[^/]+)/delete/$', views.entry_delete_view, name='entry-delete'),
    re_path(r'^(?P<slug>[^/]+)/assign/$', views.entry_assign_view, name='entry-assign'),
    re_path(r'^(?P<slug>[^/]+)/assign/me/$', views.entry_assign_me_view, name='entry-assign-me'),
    re_path(r'^(?P<slug>[^/]+)/unassign/$', views.entry_unassign_view, name='entry-unassign'),
    re_path(r'^(?P<slug>[^/]+)/complete/$', views.entry_complete_view, name='entry-complete'),
    re_path(r'^(?P<slug>[^/]+)/complete/me/$', views.entry_complete_me_view, name='entry-complete-me'),
    re_path(r'^(?P<slug>[^/]+)/incomplete/$', views.entry_incomplete_view, name='entry-incomplete'),
    re_path(r'^(?P<todo_slug>[^/]+)/comment/$', views.comment_create, name='comment'),
    re_path(r'^comment/(?P<pk>\d+)/$', views.comment_detail, name='comment-detail'),
    re_path(r'^comment/(?P<pk>\d+)/delete/$', views.comment_delete, name='comment-delete'),
    re_path(r'^comment/(?P<pk>\d+)/update/$', views.comment_update, name='comment-update'),
]

# namespace for these is 'cosinnus-api'
cosinnus_api_patterns = api_patterns(
    1,
    'todo',
    True,
    # re_path(r'^todolist/list/$', views.todolist_list_view_api', name='todolist-list'),
    # re_path(r'^todolist/list/(?P<pk>[0-9a-zA-Z_-]+)/$', views.todolist_detail_view_api', name='todolist-get'),
    # re_path(r'^todolist/add/$', views.todolist_add_view_api', name='todolist-add'),
    # re_path(r'^todolist/delete/(?P<pk>[0-9a-zA-Z_-]+)/$', views.todolist_delete_view_api', name='todolist-delete'),
    # re_path(r'^todolist/update/(?P<pk>[0-9a-zA-Z_-]+)/$', views.todolist_edit_view_api', name='todolist-update'),
    # TODO SASCHA: change 'todos' to 'todo'
    re_path(r'^todos/list/$', views.entry_list_view_api, name='todo-list-api'),
    re_path(r'^todos/list/(?P<pk>[0-9a-zA-Z_-]+)/$', views.entry_detail_view_api, name='todo-get'),
    re_path(r'^todos/add/$', views.entry_add_view_api, name='todo-add'),
    re_path(r'^todos/delete/(?P<pk>[0-9a-zA-Z_-]+)/$', views.entry_delete_view_api, name='todo-delete'),
    re_path(r'^todos/update/(?P<pk>[0-9a-zA-Z_-]+)/$', views.entry_edit_view_api, name='todo-update'),
    re_path(r'^todos/(?P<pk>[0-9a-zA-Z_-]+)/assign/$', views.entry_assign_view_api, name='entry-assign'),
    re_path(r'^todos/(?P<pk>[0-9a-zA-Z_-]+)/assign/me/$', views.entry_assign_me_view_api, name='entry-assign-me'),
    re_path(r'^todos/(?P<pk>[0-9a-zA-Z_-]+)/unassign/$', views.entry_unassign_view_api, name='entry-unassign'),
    re_path(r'^todos/(?P<pk>[0-9a-zA-Z_-]+)/complete/$', views.entry_complete_view_api, name='entry-complete'),
    re_path(r'^todos/(?P<pk>[0-9a-zA-Z_-]+)/complete/me/$', views.entry_complete_me_view_api, name='entry-complete-me'),
    re_path(
        r'^todos/(?P<pk>[0-9a-zA-Z_-]+)/toggle_complete/me/$',
        views.entry_toggle_complete_me_view_api,
        name='entry-toggle-complete-me',
    ),
    re_path(r'^todos/(?P<pk>[0-9a-zA-Z_-]+)/incomplete/$', views.entry_incomplete_view_api, name='entry-incomplete'),
)

cosinnus_root_patterns = []


urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
