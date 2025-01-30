# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import re_path

from cosinnus_marketplace import views

app_name = 'marketplace'

cosinnus_group_patterns = [
    re_path(r'^$', views.index_view, name='index-redirect'),
    re_path(r'^list/$', views.offer_list_view, name='index', kwargs={'offer_view': 'all'}),
    re_path(r'^list/$', views.offer_list_view, name='list', kwargs={'offer_view': 'all'}),
    re_path(r'^list/mine/$', views.offer_list_view, name='list_mine', kwargs={'offer_view': 'mine'}),
    re_path(r'^list/delete_element/$', views.delete_element_view, name='delete-element'),
    re_path(r'^add/$', views.offer_add_view, {'form_view': 'add'}, name='add'),
    re_path(r'^(?P<slug>[^/]+)/$', views.offer_detail_view, {'form_view': 'edit'}, name='detail'),
    re_path(r'^(?P<slug>[^/]+)/edit/$', views.offer_edit_view, {'form_view': 'edit'}, name='edit'),
    re_path(r'^(?P<slug>[^/]+)/delete/$', views.offer_delete_view, {'form_view': 'delete'}, name='delete'),
    re_path(
        r'^(?P<slug>[^/]+)/activate/$', views.offer_activate_or_deactivate_view, {'mode': 'activate'}, name='activate'
    ),
    re_path(
        r'^(?P<slug>[^/]+)/deactivate/$',
        views.offer_activate_or_deactivate_view,
        {'mode': 'deactivate'},
        name='deactivate',
    ),
    re_path(r'^(?P<offer_slug>[^/]+)/comment/$', views.comment_create, name='comment'),
    re_path(r'^comment/(?P<pk>\d+)/$', views.comment_detail, name='comment-detail'),
    re_path(r'^comment/(?P<pk>\d+)/delete/$', views.comment_delete, name='comment-delete'),
    re_path(r'^comment/(?P<pk>\d+)/update/$', views.comment_update, name='comment-update'),
]


cosinnus_root_patterns = []
urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
