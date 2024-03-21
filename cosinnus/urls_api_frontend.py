# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import path

from cosinnus.api_frontend.views.content import MainContentView
from cosinnus.api_frontend.views.user import LoginView, SignupView, UserProfileView, \
    LogoutView, UserAuthInfoView
from cosinnus.api_frontend.views.navigation import BookmarksView, SpacesView, UnreadMessagesView, UnreadAlertsView, \
    AlertsView, HelpView, ProfileView, MainNavigationView, VersionHistoryView, VersionHistoryUnreadCountView
from cosinnus.core.registries.group_models import group_model_registry
from cosinnus.api_frontend.views.portal import PortalTopicsView,\
    PortalManagedTagsView, PortalTagsView, PortalUserprofileDynamicFieldsView,\
    PortalUserprofileDynamicFieldsSignupView, PortalSettingsView


urlpatterns = []

for url_key in group_model_registry:
    prefix = group_model_registry.get_url_name_prefix(url_key, '')
    # add project/group/conference-specific URLs like this
    urlpatterns += [
        #path(f'{url_key}/<str:group>/members/', select2.group_members, name=prefix+'group-members'),
    ]

urlpatterns += [
    path('api/v3/login/', LoginView.as_view(), name='api-login'),
    path('api/v3/logout/', LogoutView.as_view(), name='api-logout'),
    path('api/v3/authinfo/', UserAuthInfoView.as_view(), name='api-authinfo'),
    path('api/v3/signup/', SignupView.as_view(), name='api-signup'),
    path('api/v3/user/profile/', UserProfileView.as_view(), name='api-user-profile'),

    path('api/v3/portal/topics/', PortalTopicsView.as_view(), name='api-portal-topics'),
    path('api/v3/portal/tags/', PortalTagsView.as_view(), name='api-portal-tags'),
    path('api/v3/portal/managed_tags/', PortalManagedTagsView.as_view(), name='api-portal-managed-tags'),
    path('api/v3/portal/userprofile_dynamicfields/signup/', PortalUserprofileDynamicFieldsSignupView.as_view(), name='api-portal-userprofile-dynamicfields-signup'),
    path('api/v3/portal/userprofile_dynamicfields/', PortalUserprofileDynamicFieldsView.as_view(), name='api-portal-userprofile-dynamicfields'),
    path('api/v3/portal/settings/', PortalSettingsView.as_view(), name='api-portal-settings'),

    path('api/v3/content/main/', MainContentView.as_view(), name='api-content-main'),
    

    path('api/v3/navigation/main/', MainNavigationView.as_view(), name='api-navigation-main'),
    path('api/v3/navigation/spaces/', SpacesView.as_view(), name='api-navigation-spaces'),
    path('api/v3/navigation/bookmarks/', BookmarksView.as_view(), name='api-navigation-bookmarks'),
    path('api/v3/navigation/unread_messages/', UnreadMessagesView.as_view(), name='api-navigation-unread-messages'),
    path('api/v3/navigation/unread_alerts/', UnreadAlertsView.as_view(), name='api-navigation-unread-alerts'),
    path('api/v3/navigation/alerts/', AlertsView.as_view(), name='api-navigation-alerts'),
    path('api/v3/navigation/help/', HelpView.as_view(), name='api-navigation-help'),
    path('api/v3/navigation/profile/', ProfileView.as_view(), name='api-navigation-profile'),
    path('api/v3/navigation/version_history/', VersionHistoryView.as_view(), name='api-navigation-version-history'),
    path('api/v3/navigation/unread_version_history/', VersionHistoryUnreadCountView.as_view(), name='api-navigation-unread-version-history'),
]