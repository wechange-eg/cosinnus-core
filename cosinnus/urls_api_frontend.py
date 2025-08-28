# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import include, path

from cosinnus.api_frontend.views.content import MainContentView
from cosinnus.api_frontend.views.navigation import (
    AlertsMarkAllReadView,
    AlertsView,
    BookmarksView,
    HelpView,
    MainNavigationView,
    MembershipAlertsView,
    ProfileView,
    SpacesView,
    UnreadAlertsView,
    UnreadMessagesView,
    VersionHistoryUnreadCountView,
    VersionHistoryView,
)
from cosinnus.api_frontend.views.portal import (
    PortalManagedTagsView,
    PortalSettingsView,
    PortalTagsView,
    PortalTopicsView,
    PortalUserprofileDynamicFieldsSignupView,
    PortalUserprofileDynamicFieldsView,
)
from cosinnus.api_frontend.views.user import (
    GroupInviteTokenView,
    GuestAccessTokenView,
    GuestLoginView,
    LoginView,
    LogoutView,
    SetInitialPasswordView,
    SignupView,
    UserAdminCreateView,
    UserAdminUpdateView,
    UserAuthInfoView,
    UserProfileView,
    UserUIFlagsView,
)
from cosinnus.conf import settings
from cosinnus.core.registries.group_models import group_model_registry

urlpatterns = []

for url_key in group_model_registry:
    prefix = group_model_registry.get_url_name_prefix(url_key, '')
    # add project/group/conference-specific URLs like this
    urlpatterns += [
        # path(f'{url_key}/<str:group>/members/', select2.group_members, name=prefix+'group-members'),
    ]

urlpatterns += [
    path('api/v3/login/', LoginView.as_view(), name='api-login'),
    path('api/v3/logout/', LogoutView.as_view(), name='api-logout'),
    path('api/v3/authinfo/', UserAuthInfoView.as_view(), name='api-authinfo'),
    path('api/v3/signup/', SignupView.as_view(), name='api-signup'),
    path('api/v3/guest_login/<str:guest_token>/', GuestLoginView.as_view(), name='api-guest-login'),
    path('api/v3/guest_access/<str:guest_token>/', GuestAccessTokenView.as_view(), name='api-guest-access-token'),
    path('api/v3/set_initial_password/<str:token>/', SetInitialPasswordView.as_view(), name='api-set-initial-password'),
    path('api/v3/group_invite/<str:token>/', GroupInviteTokenView.as_view(), name='api-group-invite-token'),
    path('api/v3/user/profile/', UserProfileView.as_view(), name='api-user-profile'),
    path('api/v3/user/create/', UserAdminCreateView.as_view(), name='api-user-admin-create'),
    path('api/v3/user/update/<int:user_id>/', UserAdminUpdateView.as_view(), name='api-user-admin-update'),
    path('api/v3/user/ui_flags/', UserUIFlagsView.as_view(), name='api-user-ui-flags'),
    path('api/v3/portal/topics/', PortalTopicsView.as_view(), name='api-portal-topics'),
    path('api/v3/portal/tags/', PortalTagsView.as_view(), name='api-portal-tags'),
    path('api/v3/portal/managed_tags/', PortalManagedTagsView.as_view(), name='api-portal-managed-tags'),
    path(
        'api/v3/portal/userprofile_dynamicfields/signup/',
        PortalUserprofileDynamicFieldsSignupView.as_view(),
        name='api-portal-userprofile-dynamicfields-signup',
    ),
    path(
        'api/v3/portal/userprofile_dynamicfields/',
        PortalUserprofileDynamicFieldsView.as_view(),
        name='api-portal-userprofile-dynamicfields',
    ),
    path('api/v3/portal/settings/', PortalSettingsView.as_view(), name='api-portal-settings'),
    path('api/v3/content/main/', MainContentView.as_view(), name='api-content-main'),
    path('api/v3/navigation/main/', MainNavigationView.as_view(), name='api-navigation-main'),
    path('api/v3/navigation/spaces/', SpacesView.as_view(), name='api-navigation-spaces'),
    path('api/v3/navigation/bookmarks/', BookmarksView.as_view(), name='api-navigation-bookmarks'),
    path('api/v3/navigation/unread_messages/', UnreadMessagesView.as_view(), name='api-navigation-unread-messages'),
    path('api/v3/navigation/unread_alerts/', UnreadAlertsView.as_view(), name='api-navigation-unread-alerts'),
    path('api/v3/navigation/alerts/', AlertsView.as_view(), name='api-navigation-alerts'),
    path(
        'api/v3/navigation/mark_all_alerts_read/',
        AlertsMarkAllReadView.as_view(),
        name='api-navigation-alerts-mark-all-read',
    ),
    path(
        'api/v3/navigation/membership_alerts/', MembershipAlertsView.as_view(), name='api-navigation-membership-alerts'
    ),
    path('api/v3/navigation/help/', HelpView.as_view(), name='api-navigation-help'),
    path('api/v3/navigation/profile/', ProfileView.as_view(), name='api-navigation-profile'),
    path('api/v3/navigation/version_history/', VersionHistoryView.as_view(), name='api-navigation-version-history'),
    path(
        'api/v3/navigation/unread_version_history/',
        VersionHistoryUnreadCountView.as_view(),
        name='api-navigation-unread-version-history',
    ),
]

if settings.COSINNUS_DECK_ENABLED:
    urlpatterns += [
        path('', include(('cosinnus_deck.urls_api_frontend', 'cosinnus'), namespace='deck-api')),
    ]
