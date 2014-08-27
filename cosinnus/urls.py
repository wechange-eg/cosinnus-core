# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import include, patterns, url

from cosinnus.core.registries import url_registry
from cosinnus.conf import settings

urlpatterns = patterns('cosinnus.views',
    url(r'^$', 'common.index', name='index'),

    url(r'^signup/$', 'user.user_create', name='user-add'),
    url(r'^users/$', 'user.user_list', name='user-list'),
    url(r'^user/(?P<username>[^/]+)/$', 'profile.detail_view', name='profile-detail'),
    #url(r'^user/(?P<username>[^/]+)/edit/$', 'user.user_update', name='user-edit'),
    url(r'^profile/$', 'profile.detail_view', name='profile-detail'),
    url(r'^profile/dashboard/$', 'widget.user_dashboard', name='user-dashboard'),
    url(r'^profile/edit/$', 'profile.update_view', name='profile-edit'),
    
    url(r'^widgets/list/$', 'widget.widget_list', name='widget-list'),
    url(r'^widgets/new/$', 'widget.widget_new', name='widget-new'),
    url(r'^widgets/add/user/(?P<app_name>[^/]+)/(?P<widget_name>[^/]+)/$', 'widget.widget_add_user', name='widget-add-user'),
    url(r'^widgets/add/%s/(?P<group>[^/]+)/(?P<app_name>[^/]+)/(?P<widget_name>[^/]+)/$' % settings.COSINNUS_GROUP_URL_PATH, 'widget.widget_add_group', name='widget-add-group'),
    url(r'^widget/(?P<id>\d+)/$', 'widget.widget_detail', name='widget-detail'),
    url(r'^widget/(?P<id>\d+)/(?P<offset>\d+)/$', 'widget.widget_detail', name='widget-detail-offset'),
    url(r'^widget/(?P<id>\d+)/delete/$', 'widget.widget_delete', name='widget-delete'),
    url(r'^widget/(?P<id>\d+)/edit/$', 'widget.widget_edit', name='widget-edit'),
    url(r'^widget/(?P<id>\d+)/edit/(?P<app_name>[^/]+)/(?P<widget_name>[^/]+)/$', 'widget.widget_edit', name='widget-edit-swap'),

    url(r'^%s/$' % settings.COSINNUS_GROUP_PLURAL_URL_PATH, 'group.group_list', name='group-list'),
    url(r'^%s/map/$' % settings.COSINNUS_GROUP_PLURAL_URL_PATH, 'group.group_list_map', name='group-list-map'),
    url(r'^%s/add/$' % settings.COSINNUS_GROUP_PLURAL_URL_PATH, 'group.group_create', name='group-add'),
    url(r'^%s/(?P<group>[^/]+)/$' % settings.COSINNUS_GROUP_URL_PATH, 'widget.group_dashboard', name='group-dashboard'),
    url(r'^%s/(?P<group>[^/]+)/microsite/$' % settings.COSINNUS_GROUP_URL_PATH, 'cms.group_microsite', name='group-microsite'),
    url(r'^%s/(?P<group>[^/]+)/members/$' % settings.COSINNUS_GROUP_URL_PATH, 'group.group_detail', name='group-detail'),
    url(r'^%s/(?P<group>[^/]+)/edit/$' % settings.COSINNUS_GROUP_URL_PATH, 'group.group_update', name='group-edit'),
    url(r'^%s/(?P<group>[^/]+)/delete/$' % settings.COSINNUS_GROUP_URL_PATH, 'group.group_delete', name='group-delete'),
    url(r'^%s/(?P<group>[^/]+)/join/$' % settings.COSINNUS_GROUP_URL_PATH, 'group.group_user_join', name='group-user-join'),
    url(r'^%s/(?P<group>[^/]+)/leave/$' % settings.COSINNUS_GROUP_URL_PATH, 'group.group_user_leave', name='group-user-leave'),
    url(r'^%s/(?P<group>[^/]+)/withdraw/$' % settings.COSINNUS_GROUP_URL_PATH, 'group.group_user_withdraw', name='group-user-withdraw'),
    url(r'^%s/(?P<group>[^/]+)/users/$' % settings.COSINNUS_GROUP_URL_PATH, 'group.group_user_list', name='group-user-list'),
    url(r'^%s/(?P<group>[^/]+)/users/add/$' % settings.COSINNUS_GROUP_URL_PATH, 'group.group_user_add', name='group-user-add-generic'),
    url(r'^%s/(?P<group>[^/]+)/users/add/(?P<username>[^/]+)/$' % settings.COSINNUS_GROUP_URL_PATH, 'group.group_user_add', name='group-user-add'),
    url(r'^%s/(?P<group>[^/]+)/users/delete/(?P<username>[^/]+)/$' % settings.COSINNUS_GROUP_URL_PATH, 'group.group_user_delete', name='group-user-delete'),
    url(r'^%s/(?P<group>[^/]+)/users/edit/(?P<username>[^/]+)/$' % settings.COSINNUS_GROUP_URL_PATH, 'group.group_user_update', name='group-user-edit'),
    url(r'^%s/(?P<group>[^/]+)/export/$' % settings.COSINNUS_GROUP_URL_PATH, 'group.group_export', name='group-export'),

    url(r'^attachmentselect/(?P<group>[^/]+)/(?P<model>[^/]+)$', 'attached_object.attachable_object_select2_view', name='attached_object_select2_view'),

    url(r'^search/$', 'search.search', name='search'),

    url(r'^select2/', include('cosinnus.urls_select2', namespace='select2')),
)

urlpatterns += url_registry.urlpatterns
