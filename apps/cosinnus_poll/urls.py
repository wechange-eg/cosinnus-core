# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url
from cosinnus_poll import views

app_name = 'poll'

cosinnus_group_patterns = [
    url(r'^$', views.index_view, name='index'),
    url(r'^list/$', views.poll_list_view, name='list', kwargs={'poll_view': 'current'}),
    url(r'^list/past/$', views.poll_list_view, name='list_past', kwargs={'poll_view': 'past'}),
    url(r'^list/delete_element/$', views.delete_element_view, name='delete-element'),
    url(r'^add/$', views.poll_add_view,  {'form_view': 'add'},  name='add'),
    url(r'^(?P<slug>[^/]+)/$', views.poll_vote_view, {'form_view': 'edit'},  name='detail'),
    url(r'^(?P<slug>[^/]+)/edit/$', views.poll_edit_view, {'form_view': 'edit'}, name='edit'),
    url(r'^(?P<slug>[^/]+)/delete/$', views.poll_delete_view, {'form_view': 'delete'}, name='delete'),
    url(r'^(?P<slug>[^/]+)/complete/$', views.poll_complete_view, name='complete', kwargs={'mode': 'complete'}),
    url(r'^(?P<slug>[^/]+)/complete/(?P<option_id>\d+)/$', views.poll_complete_view, name='complete', kwargs={'mode': 'complete'}),
    url(r'^(?P<slug>[^/]+)/reopen/$', views.poll_complete_view, name='reopen', kwargs={'mode': 'reopen'}),
    url(r'^(?P<slug>[^/]+)/archive/$', views.poll_complete_view, name='archive', kwargs={'mode': 'archive'}),

    url(r'^(?P<poll_slug>[^/]+)/comment/$', views.comment_create, name='comment'),
    url(r'^comment/(?P<pk>\d+)/$', views.comment_detail, name='comment-detail'),
    url(r'^comment/(?P<pk>\d+)/delete/$', views.comment_delete, name='comment-delete'),
    url(r'^comment/(?P<pk>\d+)/update/$', views.comment_update, name='comment-update'),
]

cosinnus_root_patterns = []


urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns
