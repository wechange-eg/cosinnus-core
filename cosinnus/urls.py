# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import patterns, url

from cosinnus.core.loaders.urls import cosinnus_site


urlpatterns = patterns('cosinnus.views',
    url(r'^profile/$', 'profile.detail_view', name='profile-detail'),
    url(r'^profile/edit/$', 'profile.update_view', name='profile-edit'),

    url(r'^groups/$', 'group.group_list', name='group-list'),
    url(r'^group/(?P<group>\d+)/$', 'group.group_detail', name='group-detail'),
    url(r'^group/(?P<group>\d+)/users/$', 'group.group_user_list', name='group-user-list'),
    url(r'^group/(?P<group>\d+)/user/(?P<username>[^/]+)/add/$', 'group.group_user_add', name='group-user-add'),
    url(r'^group/(?P<group>\d+)/user/(?P<username>[^/]+)/delete/$', 'group.group_user_delete', name='group-user-delete'),

    url(r'^users/$', 'user.user_list', name='user-list'),
    url(r'^users/add/$', 'user.user_create', name='user-add'),
    url(r'^user/(?P<username>[^/]+)/$', 'user.user_detail', name='user-detail'),
    url(r'^user/(?P<username>[^/]+)/edit/$', 'user.user_update', name='user-edit'),
)

cosinnus_site.autodiscover()
urlpatterns += cosinnus_site.urlpatterns
