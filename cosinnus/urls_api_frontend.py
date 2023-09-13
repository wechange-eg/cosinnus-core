# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url

from cosinnus.api_frontend.views.user import LoginView, SignupView, UserProfileView, \
    LogoutView, UserAuthInfoView
from cosinnus.api_frontend.views.navigation import BookmarksView, SpacesView, UnreadMessagesView, UnreadAlertsView, \
    AlertsView, HelpView, ProfileView, ServicesView
from cosinnus.core.registries.group_models import group_model_registry
from cosinnus.api_frontend.views.portal import PortalTopicsView,\
    PortalManagedTagsView, PortalTagsView, PortalUserprofileDynamicFieldsView,\
    PortalUserprofileDynamicFieldsSignupView


urlpatterns = []

for url_key in group_model_registry:
    prefix = group_model_registry.get_url_name_prefix(url_key, '')
    # add project/group/conference-specific URLs like this
    urlpatterns += [
        #url(r'%s/(?P<group>[^/]+)/members/$' % url_key, select2.group_members, name=prefix+'group-members'),
    ]

urlpatterns += [
    url(r'^api/v3/login/$', LoginView.as_view(), name='api-login'),
    url(r'^api/v3/logout/$', LogoutView.as_view(), name='api-logout'),
    url(r'^api/v3/authinfo/$', UserAuthInfoView.as_view(), name='api-authinfo'),
    url(r'^api/v3/signup/$', SignupView.as_view(), name='api-signup'),
    url(r'^api/v3/user/profile/$', UserProfileView.as_view(), name='api-user-profile'),

    url(r'^api/v3/portal/topics/$', PortalTopicsView.as_view(), name='api-portal-topics'),
    url(r'^api/v3/portal/tags/$', PortalTagsView.as_view(), name='api-portal-tags'),
    url(r'^api/v3/portal/managed_tags/$', PortalManagedTagsView.as_view(), name='api-portal-managed-tags'),
    url(r'^api/v3/portal/userprofile_dynamicfields/signup/$', PortalUserprofileDynamicFieldsSignupView.as_view(), name='api-portal-userprofile-dynamicfields-signup'),
    url(r'^api/v3/portal/userprofile_dynamicfields/$', PortalUserprofileDynamicFieldsView.as_view(), name='api-portal-userprofile-dynamicfields'),

    url(r'^api/v3/navigation/spaces/$', SpacesView.as_view(), name='api-navigation-spaces'),
    url(r'^api/v3/navigation/bookmarks/$', BookmarksView.as_view(), name='api-navigation-bookmarks'),
    url(r'^api/v3/navigation/unread_messages/$', UnreadMessagesView.as_view(), name='api-navigation-unread-messages'),
    url(r'^api/v3/navigation/unread_alerts/$', UnreadAlertsView.as_view(), name='api-navigation-unread-alerts'),
    url(r'^api/v3/navigation/alerts/$', AlertsView.as_view(), name='api-navigation-alerts'),
    url(r'^api/v3/navigation/help/$', HelpView.as_view(), name='api-navigation-help'),
    url(r'^api/v3/navigation/profile/$', ProfileView.as_view(), name='api-navigation-profile'),
    url(r'^api/v3/navigation/services/$', ServicesView.as_view(), name='api-navigation-services'),
]