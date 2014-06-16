# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import include, patterns, url

from cosinnus.core.registries import url_registry


urlpatterns = patterns('cosinnus.views',
    url(r'^$', 'common.index', name='index'),

    url(r'^profile/$', 'profile.detail_view', name='profile-detail'),
    url(r'^profile/dashboard/$', 'widget.user_dashboard', name='user-dashboard'),
    url(r'^profile/edit/$', 'profile.update_view', name='profile-edit'),

    url(r'^widgets/list/$', 'widget.widget_list', name='widget-list'),
    url(r'^widgets/add/user/(?P<app_name>[^/]+)/(?P<widget_name>[^/]+)/$', 'widget.widget_add_user', name='widget-add-user'),
    url(r'^widgets/add/group/(?P<group>[^/]+)/(?P<app_name>[^/]+)/(?P<widget_name>[^/]+)/$', 'widget.widget_add_group', name='widget-add-group'),
    url(r'^widget/(?P<id>\d+)/$', 'widget.widget_detail', name='widget-detail'),
    url(r'^widget/(?P<id>\d+)/delete/$', 'widget.widget_delete', name='widget-delete'),
    url(r'^widget/(?P<id>\d+)/edit/$', 'widget.widget_edit', name='widget-edit'),

    url(r'^groups/$', 'group.group_list', name='group-list'),
    url(r'^groups/add/$', 'group.group_create', name='group-add'),
    url(r'^group/(?P<group>[^/]+)/$', 'widget.group_dashboard', name='group-dashboard'),
    url(r'^group/(?P<group>[^/]+)/details/$', 'group.group_detail', name='group-detail'),
    url(r'^group/(?P<group>[^/]+)/edit/$', 'group.group_update', name='group-edit'),
    url(r'^group/(?P<group>[^/]+)/delete/$', 'group.group_delete', name='group-delete'),
    url(r'^group/(?P<group>[^/]+)/join/$', 'group.group_user_join', name='group-user-join'),
    url(r'^group/(?P<group>[^/]+)/leave/$', 'group.group_user_leave', name='group-user-leave'),
    url(r'^group/(?P<group>[^/]+)/withdraw/$', 'group.group_user_withdraw', name='group-user-withdraw'),
    url(r'^group/(?P<group>[^/]+)/users/$', 'group.group_user_list', name='group-user-list'),
    url(r'^group/(?P<group>[^/]+)/users/add/$', 'group.group_user_add', name='group-user-add-generic'),
    url(r'^group/(?P<group>[^/]+)/users/add/(?P<username>[^/]+)/$', 'group.group_user_add', name='group-user-add'),
    url(r'^group/(?P<group>[^/]+)/users/delete/(?P<username>[^/]+)/$', 'group.group_user_delete', name='group-user-delete'),
    url(r'^group/(?P<group>[^/]+)/users/edit/(?P<username>[^/]+)/$', 'group.group_user_update', name='group-user-edit'),
    url(r'^group/(?P<group>[^/]+)/export/$', 'group.group_export', name='group-export'),

    url(r'^users/$', 'user.user_list', name='user-list'),
    url(r'^signup/$', 'user.user_create', name='user-add'),
    url(r'^user/(?P<username>[^/]+)/$', 'user.user_detail', name='user-detail'),
    url(r'^user/(?P<username>[^/]+)/edit/$', 'user.user_update', name='user-edit'),

    url(r'^attachmentselect/(?P<group>[^/]+)/(?P<model>[^/]+)$', 'attached_object.attachable_object_select2_view', name='attached_object_select2_view'),

    url(r'^search/$', 'search.search', name='search'),

    url(r'^select2/', include('cosinnus.urls_select2', namespace='select2')),
)

urlpatterns += url_registry.urlpatterns
