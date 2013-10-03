# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import patterns, url


urlpatterns = patterns('cosinnus.core.views',
    url(r'^profile/$', 'profile.detail_view', name='profile-detail'),
    url(r'^profile/edit/$', 'profile.update_view', name='profile-update'),


    url(r'^groups/$', 'group.group_list', name='group-list'),
    url(r'^group/(?P<group>\d+)/$', 'group.group_detail', name='group-detail'),

    url(r'^group/(?P<group>\d+)/users/$', 'user.user_list', name='user-list'),
    url(r'^group/(?P<group>\d+)/users/add/$', 'user.user_create', name='user-add'),
    url(r'^group/(?P<group>\d+)/user/(?P<pk>\d+)/$', 'user.user_detail', name='user-detail'),
    url(r'^group/(?P<group>\d+)/user/(?P<user>\d+)/add/$', 'user.user_add_group', name='user-add-group'),
    url(r'^group/(?P<group>\d+)/user/(?P<user>\d+)/remove/$', 'user.user_remove_group', name='user-remove-group'),
)
