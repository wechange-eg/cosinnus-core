# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.templatetags.static import static
from django.urls import include, path, re_path, reverse_lazy
from django.views.generic.base import RedirectView, TemplateView
from drf_yasg import openapi
from drf_yasg.generators import OpenAPISchemaGenerator
from drf_yasg.views import get_schema_view
from rest_framework import permissions, routers
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from cosinnus.api.views.group import (
    CosinnusProjectExchangeViewSet,
    CosinnusProjectViewSet,
    CosinnusSocietyExchangeViewSet,
    CosinnusSocietyViewSet,
)
from cosinnus.api.views.i18n import translations
from cosinnus.api.views.portal import config as api_config
from cosinnus.api.views.portal import footer, header
from cosinnus.api.views.portal import settings as api_settings
from cosinnus.api.views.portal import statistics as api_statistics
from cosinnus.api.views.user import UserViewSet, current_user, oauth_current_user, oauth_profile, oauth_user
from cosinnus.conf import settings
from cosinnus.core.registries import url_registry
from cosinnus.core.registries.group_models import group_model_registry
from cosinnus.templatetags.cosinnus_tags import is_integrated_portal, is_sso_portal
from cosinnus.views import (
    administration,
    attached_object,
    authentication,
    bbb_room,
    common,
    conference_administration,
    dynamic_fields,
    facebook_integration,
    feedback,
    group,
    housekeeping,
    idea,
    map,
    map_api,
    microsite,
    mitwirkomat,
    profile,
    search,
    statistics,
    ui_prefs,
    user,
    user_dashboard,
    user_dashboard_announcement,
    user_export,
    user_import,
    user_match,
    version_history,
    widget,
)
from cosinnus_conference.api.views import ConferenceViewSet, PublicConferenceViewSet
from cosinnus_organization.api.views import OrganizationViewSet

app_name = 'cosinnus'

urlpatterns = [
    # we do not define an index anymore and let CMS handle that.
    path('favicon.ico', RedirectView.as_view(url=static('images/favicon.ico'), permanent=False)),
    path(
        'apple-touch-icon.png',
        RedirectView.as_view(url=static('images/apple-touch-icon-114x114-precomposed.png'), permanent=False),
    ),
    path(
        'apple-touch-icon-precomposed.png',
        RedirectView.as_view(url=static('images/apple-touch-icon-114x114-precomposed.png'), permanent=False),
    ),
    path('users/', map.tile_view, name='user-list', kwargs={'types': ['people']}),
    path('portal/admins/', user.portal_admin_list, name='portal-admin-list'),
    path('user/<str:username>/', profile.detail_view, name='profile-detail'),
    path('language/<str:language>/', common.switch_language, name='switch-language'),
    path('widgets/list/', widget.widget_list, name='widget-list'),
    path('widgets/add/user/', widget.widget_add_user, name='widget-add-user-empty'),
    path('widgets/add/user/<str:app_name>/<str:widget_name>/', widget.widget_add_user, name='widget-add-user'),
    path('widgets/save/', widget.save_widget_config, name='widget-save-config'),
    path('widget/<int:id>/', widget.widget_detail, name='widget-detail'),
    path('widget/<int:id>/<int:offset>/', widget.widget_detail, name='widget-detail-offset'),
    path('widget/<int:id>/delete/', widget.widget_delete, name='widget-delete'),
    path('widget/<int:id>/edit/', widget.widget_edit, name='widget-edit'),
    path('widget/<int:id>/edit/<str:app_name>/<str:widget_name>/', widget.widget_edit, name='widget-edit-swap'),
    path('search/', search.search, name='search'),
    path('map/', map.map_view, name='map'),
    path('projects/', map.tile_view, name='group-list', kwargs={'types': ['projects']}),
    path('groups/', map.tile_view, name='group__group-list', kwargs={'types': ['groups']}),
    path('conferences/', map.tile_view, name='conference__group-list', kwargs={'types': ['conferences']}),
    path('projects/mine/', map.tile_view, name='group-list-mine', kwargs={'types': ['projects'], 'show_mine': True}),
    path('groups/mine/', map.tile_view, name='group__group-list-mine', kwargs={'types': ['groups'], 'show_mine': True}),
    path('map/embed/', map.map_embed_view, name='map-embed'),
    path('map/search/', map_api.map_search_endpoint, name='map-search-endpoint'),
    path('map/search/<int:filter_group_id>/', map_api.map_search_endpoint, name='map-search-endpoint-filtered'),
    path('map/detail/', map_api.map_detail_endpoint, name='map-detail-endpoint'),
    path('likefollowstar/', common.do_likefollowstar, name='likefollowstar-view'),
    path('bbb/room/<int:room_id>/', bbb_room.bbb_room_meeting, name='bbb-room'),
    path('bbb/queue/<int:mt_id>/', bbb_room.bbb_room_meeting_queue, name='bbb-room-queue'),
    path('bbb/queue-api/<int:mt_id>/', bbb_room.bbb_room_meeting_queue_api, name='bbb-room-queue-api'),
    path('bbb/<str:guest_token>/', bbb_room.bbb_room_guest_access, name='bbb-room-guest-access'),
    path('invitations/', group.group_list_invited, name='invitations', kwargs={'show_all': True}),
    path('welcome/', user.welcome_settings, name='welcome-settings'),
    path('join/', user.group_invite_token_enter_view, name='group-invite-token-enter'),
    path('join/<str:token>/', user.group_invite_token_view, name='group-invite-token'),
    path('guest_restricted/', user.guest_user_not_allowed_view, name='guest-user-not-allowed'),
    path('guest/<str:guest_token>/', user.guest_user_signup_view, name='guest-user-signup'),
    path('whats_new/', version_history.version_history, name='version-history'),
    path('list-unsubscribe-result/', user.add_email_to_blacklist_result, name='user-add-email-blacklist-result'),
    # /account/ URLs: Note that no views should be placed under the /account/ path that show user UI pages or
    # that require input! Only service-endpoints that redirect elsewhere or are used as AJAX should be here.
    path('account/report/', feedback.report_object, name='report-object'),
    path('account/accept_tos/', user.accept_tos, name='accept-tos'),
    path('account/resend_email_validation/', user.resend_email_validation, name='resend-email-validation'),
    path('account/accept_updated_tos/', user.accept_updated_tos, name='accept-updated-tos'),
    path(
        'account/list-unsubscribe/<str:email>/<str:token>/',
        user.add_email_to_blacklist,
        name='user-add-email-blacklist',
    ),
    path('account/verify_email/<str:email_verification_param>/', user.verifiy_user_email, name='user-verifiy-email'),
    # --- DEPERECATED -----
    # these URL paths are deprecated and have been replaced by the /account/ prefix
    # they should be kept until mid-2021 so old sent-out emails do not point to a 404
    path(
        'administration/list-unsubscribe/<str:email>/<str:token>/',
        user.add_email_to_blacklist,
        name='OLD-user-add-email-blacklist',
    ),
    path(
        'administration/list-unsubscribe-result/',
        user.add_email_to_blacklist_result,
        name='OLD-user-add-email-blacklist-result',
    ),
    path('administration/deactivated/', group.group_list_mine_deactivated, name='OLD-deactivated-groups'),
    path(
        'administration/activate/<int:group_id>/',
        group.activate_or_deactivate,
        name='OLD-group-activate',
        kwargs={'activate': True},
    ),
    path(
        'administration/deactivate/<int:group_id>/',
        group.activate_or_deactivate,
        name='OLD-group-deactivate',
        kwargs={'activate': False},
    ),
    path(
        'administration/verify_email/<str:email_verification_param>/',
        user.verifiy_user_email,
        name='OLD-user-verifiy-email',
    ),
    # ---- END DEPRECATED ---
    # these URLs belong to the frontend administration area for superusers
    path('administration/', administration.administration, name='administration'),
    path('administration/login-2fa/', authentication.admin_only_otp_token_validation, name='login-2fa'),
    path('administration/approve_user/<int:user_id>/', user.approve_user, name='user-approve'),
    path('administration/deny_user/<int:user_id>/', user.deny_user, name='user-deny'),
    path('administration/welcome_email/', administration.welcome_email_edit, name='administration-welcome-email'),
    path('administration/users/', administration.user_list, name='administration-users'),
    path('administration/users/add/', administration.user_add, name='administration-user-create'),
    path(
        'administration/group_newsletter/', administration.groups_newsletters, name='administration-groups-newsletter'
    ),
    path(
        'administration/group_newsletter/add/',
        administration.groups_newsletter_create,
        name='administration-groups-newsletter-create',
    ),
    path(
        'administration/group_newsletter/<int:newsletter_id>/edit/',
        administration.groups_newsletter_update,
        name='administration-groups-newsletter-update',
    ),
    path(
        'administration/tag_newsletter/',
        administration.managed_tags_newsletters,
        name='administration-managed-tags-newsletter',
    ),
    path(
        'administration/tag_newsletter/add/',
        administration.managed_tags_newsletter_create,
        name='administration-managed-tags-newsletter-create',
    ),
    path(
        'administration/tag_newsletter/<int:newsletter_id>/edit/',
        administration.managed_tags_newsletter_update,
        name='administration-managed-tags-newsletter-update',
    ),
    path(
        'administration/announcements/', user_dashboard_announcement.list_view, name='user-dashboard-announcement-list'
    ),
    path(
        'administration/announcements/add/',
        user_dashboard_announcement.user_dashboard_announcement_create,
        name='user-dashboard-announcement-create',
    ),
    path(
        'administration/announcement/<slug:slug>/edit/',
        user_dashboard_announcement.user_dashboard_announcement_edit,
        name='user-dashboard-announcement-edit',
    ),
    path(
        'administration/announcement/<slug:slug>/delete/',
        user_dashboard_announcement.user_dashboard_announcement_delete,
        name='user-dashboard-announcement-delete',
    ),
    path(
        'administration/announcement/<slug:slug>/activate-toggle/',
        user_dashboard_announcement.user_dashboard_announcement_activate,
        name='user-dashboard-announcement-activate',
    ),
    path(
        'conference_administration/',
        conference_administration.conference_administration,
        name='conference-administration',
    ),
    path(
        'administration/conference_overview/',
        conference_administration.conference_overview,
        name='conference-administration-overview',
    ),
    path(
        'administration/conference_overview/nonstandard/',
        conference_administration.conference_overview,
        name='conference-administration-overview-nonstandard',
        kwargs={'only_nonstandard': True},
    ),
    path(
        'administration/conference_overview/premium/',
        conference_administration.conference_overview,
        name='conference-administration-overview-premium',
        kwargs={'only_premium': True},
    ),
    path(
        'administration/conference/<slug:slug>/blocks/add/',
        conference_administration.conference_add_premium_block,
        name='conference-administration-add-premium-block',
    ),
    path(
        'administration/conference/block/<int:block_id>/edit/',
        conference_administration.conference_edit_premium_block,
        name='conference-administration-edit-premium-block',
    ),
    path('statistics/simple/', statistics.simple_statistics, name='simple-statistics'),
    path(
        'housekeeping/ensure_group_widgets/',
        housekeeping.ensure_group_widgets,
        name='housekeeping-ensure-group-widgets',
    ),
    path('housekeeping/newsletterusers/', housekeeping.newsletter_users, name='housekeeping-newsletter-user-emails'),
    path('housekeeping/activeuseremails/', housekeeping.active_user_emails, name='housekeeping-active-user-emails'),
    path(
        'housekeeping/neverloggedinuseremails/',
        housekeeping.never_logged_in_user_emails,
        name='housekeeping-never-logged-in-user-emails',
    ),
    path('housekeeping/deletespamusers/', housekeeping.delete_spam_users, name='housekeeping_delete_spam_users'),
    path(
        'housekeeping/movegroupcontent/<str:fromgroup>/<str:togroup>/',
        housekeeping.move_group_content,
        name='housekeeping_move_group_content',
    ),
    path(
        'housekeeping/recreategroupwidgets/',
        housekeeping.recreate_all_group_widgets,
        name='housekeeping_recreate_all_group_widgets',
    ),
    path('housekeeping/setcache/<str:content>/', housekeeping.setcache, name='housekeeping-setcache'),
    path('housekeeping/fillcache/<str:number>/', housekeeping.fillcache, name='housekeeping-fillcache'),
    path('housekeeping/getcache', housekeeping.getcache, name='housekeeping-getcache'),
    path('housekeeping/deletecache', housekeeping.deletecache, name='housekeeping-deletecache'),
    path('housekeeping/users_online_today/', housekeeping.users_online_today, name='housekeeping-users_online_today'),
    path('housekeeping/test_logging/', housekeeping.test_logging, name='housekeeping-test-logging'),
    path(
        'housekeeping/test_logging/info/',
        housekeeping.test_logging,
        name='housekeeping-test-logging',
        kwargs={'level': 'info'},
    ),
    path(
        'housekeeping/test_logging/warning/',
        housekeeping.test_logging,
        name='housekeeping-test-logging',
        kwargs={'level': 'warning'},
    ),
    path(
        'housekeeping/test_logging/error/',
        housekeeping.test_logging,
        name='housekeeping-test-logging',
        kwargs={'level': 'error'},
    ),
    path(
        'housekeeping/test_logging/exception/',
        housekeeping.test_logging,
        name='housekeeping-test-logging',
        kwargs={'level': 'exception'},
    ),
    path(
        'housekeeping/validate_redirects/',
        housekeeping.check_and_delete_loop_redirects,
        name='housekeeping-validate-redirects',
    ),
    path(
        'housekeeping/add_members_to_forum/',
        housekeeping.add_members_to_forum,
        name='housekeeping-add-members-to-forum',
    ),
    path('housekeeping/user_statistics/', housekeeping.user_statistics, name='housekeeping-user-statistics'),
    path(
        'housekeeping/create_map_test_entities/<int:count>/',
        housekeeping.create_map_test_entities,
        name='housekeeping-create-map-test-entities',
    ),
    path(
        'housekeeping/reset_user_tos_flags/',
        housekeeping.reset_user_tos_flags,
        name='housekeeping-reset-user-tos-flags',
    ),
    path('housekeeping/send_testmail/', housekeeping.send_testmail, name='housekeeping-send-testmail'),
    path('housekeeping/print_testmail/', housekeeping.print_testmail, name='housekeeping-print-testmail'),
    path(
        'housekeeping/print_test_registration_notification_mail/',
        housekeeping.print_test_registration_notification_mail,
        name='housekeeping-print-test-registration-notification-mail',
    ),
    path(
        'housekeeping/print_digest_daily/', housekeeping.print_testdigest_daily, name='housekeeping-print-digest-daily'
    ),
    path(
        'housekeeping/print_digest_weekly/',
        housekeeping.print_testdigest_weekly,
        name='housekeeping-print-digest-weekly',
    ),
    path('housekeeping/print_settings/', housekeeping.print_settings, name='housekeeping-print-settings'),
    path(
        'housekeeping/conf_settings_info/',
        housekeeping.portal_switches_and_settings,
        name='housekeeping-portal-switches-and-settings',
    ),
    path(
        'housekeeping/group_admin_emails/<str:slugs>/',
        housekeeping.group_admin_emails,
        name='housekeeping-group-admin-emails',
    ),
    path(
        'housekeeping/firebase_send_testpush/',
        housekeeping.firebase_send_testpush,
        name='housekeeping-firebase-send-testpush',
    ),
    path('error/', common.generic_error_page_view, name='generic-error-page'),
    path('select2/', include(('cosinnus.urls_select2', 'select2'), namespace='select2')),
    path('robots.txt', common.robots_text, name='robots-text'),
]

if getattr(settings, 'COSINNUS_USER_IMPORT_ADMINISTRATION_VIEWS_ENABLED', False):
    urlpatterns += [
        path('administration/user_import/', user_import.user_import_view, name='administration-user-import'),
        path(
            'administration/user_import/archived/',
            user_import.archived_user_import_list_view,
            name='administration-archived-user-import-list',
        ),
        path(
            'administration/user_import/archived/<int:pk>/',
            user_import.archived_user_import_detail_view,
            name='administration-archived-user-import-detail',
        ),
        path(
            'administration/user_import/archived/<int:pk>/delete/',
            user_import.archived_user_import_delete_view,
            name='administration-archived-user-import-delete',
        ),
    ]

if getattr(settings, 'COSINNUS_USER_EXPORT_ADMINISTRATION_VIEWS_ENABLED', False):
    urlpatterns += [
        path('administration/user_export/', user_export.user_export_view, name='administration-user-export'),
        path(
            'administration/user_export/download/csv/',
            user_export.user_export_csv_download_view,
            name='administration-user-export-csv-download',
        ),
        path(
            'administration/user_export/download/xlsx/',
            user_export.user_export_xlsx_download_view,
            name='administration-user-export-xlsx-download',
        ),
    ]

if getattr(settings, 'COSINNUS_DYNAMIC_FIELD_ADMINISTRATION_VIEWS_ENABLED', False):
    urlpatterns += [
        path(
            'administration/admin_dynamic_fields/edit/',
            dynamic_fields.dynamic_field_admin_choices_form_view,
            name='administration-dynamic-fields',
        ),
    ]

if getattr(settings, 'COSINNUS_PLATFORM_ADMIN_CAN_EDIT_PROFILES', False):
    urlpatterns += [
        path('administration/users/<int:pk>/edit/', administration.user_update, name='administration-user-update'),
    ]

if getattr(settings, 'COSINNUS_USE_V2_DASHBOARD', False) or getattr(
    settings, 'COSINNUS_USE_V2_DASHBOARD_ADMIN_ONLY', False
):
    dashboard_url = getattr(settings, 'COSINNUS_V2_DASHBOARD_URL_FRAGMENT', 'dashboard')
    if getattr(settings, 'COSINNUS_CLOUD_SEARCH_ENABLED', False):
        urlpatterns += [
            path('search/cloudfiles/', map.tile_view, name='cloudfiles-search', kwargs={'types': ['cloudfiles']}),
        ]

    urlpatterns += [
        path(f'{dashboard_url}/', user_dashboard.user_dashboard_view, name='user-dashboard'),
        path('dashboard/api/user_groups/', user_dashboard.api_user_groups, name='user-dashboard-api-groups'),
        path(
            'dashboard/api/user_liked_ideas/',
            user_dashboard.api_user_liked_ideas,
            name='user-dashboard-api-liked-ideas',
        ),
        path(
            'dashboard/api/user_starred_users/',
            user_dashboard.api_user_starred_users,
            name='user-dashboard-api-starred-users',
        ),
        path(
            'dashboard/api/user_starred_objects/',
            user_dashboard.api_user_starred_objects,
            name='user-dashboard-api-starred-objects',
        ),
        path(
            'dashboard/api/user_followed_objects/',
            user_dashboard.api_user_followed_objects,
            name='user-dashboard-api-followed-objects',
        ),
        path(
            'dashboard/api/user_typed_content/<str:content>/',
            user_dashboard.api_user_typed_content,
            name='user-dashboard-api-typed-content',
        ),
        path(
            'dashboard/api/user_typed_content/recent/<str:content>/',
            user_dashboard.api_user_typed_content,
            name='user-dashboard-api-typed-content',
            kwargs={'show_recent': True},
        ),
        path(
            'dashboard/api/timeline/<str:content>/',
            user_dashboard.api_timeline,
            name='user-dashboard-api-timeline-filtered',
        ),
        path('dashboard/api/timeline/', user_dashboard.api_timeline, name='user-dashboard-api-timeline'),
        path('dashboard/api/save_ui_prefs/', ui_prefs.api_ui_prefs, name='user-dashboard-api-ui-prefs'),
    ]

if getattr(settings, 'COSINNUS_USE_V2_NAVBAR', False) or getattr(settings, 'COSINNUS_USE_V2_NAVBAR_ADMIN_ONLY', False):
    urlpatterns += [
        path('search/api/quicksearch/', search.api_quicksearch, name='quicksearch-api'),
        path(
            'version_history/api/markread/',
            version_history.version_history_mark_read,
            name='version-history-api-mark-read',
        ),
    ]

if getattr(settings, 'COSINNUS_ENABLE_USER_MATCH', True):
    urlpatterns += [
        path('user_match/', user_match.user_match_list_view, name='user-match'),
        path('user_match_assign/', user_match.match_create_view, name='user-match-match'),
    ]

if getattr(settings, 'COSINNUS_ENABLE_USER_BLOCK', True):
    urlpatterns += [
        path('user/<str:username>/block/', profile.user_block_view, name='block-user'),
        path('user/<str:username>/unblock/', profile.user_unblock_view, name='unblock-user'),
    ]

if settings.COSINNUS_USER_2_FACTOR_AUTH_ENABLED:
    urlpatterns += [
        path('two_factor_auth/token_login/', authentication.user_otp_token_validation, name='two-factor-auth-token'),
        path(
            'two_factor_auth/token_login/backup/',
            authentication.user_otp_token_validation,
            name='two-factor-auth-token-backup',
            kwargs={'two_factor_method': 'backup'},
        ),
        path('two_factor_auth/qrcode/', authentication.two_factor_auth_qr, name='two-factor-auth-qr'),
        path('two_factor_auth/settings/', authentication.two_factor_user_hub, name='two-factor-auth-settings'),
        path('two_factor_auth/settings/setup/', authentication.two_factor_auth_setup, name='two-factor-auth-setup'),
        path(
            'two_factor_auth/settings/setup/complete/',
            authentication.two_factor_auth_setup_complete,
            name='two-factor-auth-setup-complete',
        ),
        path(
            'two_factor_auth/settings/disable/', authentication.two_factor_auth_disable, name='two-factor-auth-disable'
        ),
        path(
            'two_factor_auth/settings/backup_tokens/',
            authentication.two_factor_auth_back_tokens,
            name='two-factor-auth-backup-tokens',
        ),
    ]

# some user management not allowed in integrated mode and sso-mode
if not is_integrated_portal() and not is_sso_portal():
    urlpatterns += [
        path('profile/edit/', profile.update_view, name='profile-edit'),
        path('signup/', user.user_create, name='user-add'),
    ]

    if not settings.COSINNUS_IS_OAUTH_CLIENT and not settings.COSINNUS_USER_LOGIN_DISABLED:
        # disable email change in SSO client mode without login
        urlpatterns += [
            path('profile/change_email/', user.change_email_view, name='user-change-email'),
            path('profile/change_email/pending/', user.change_email_pending_view, name='user-change-email-pending'),
        ]

# some more user management not allowed in integrated mode
if not is_integrated_portal():
    urlpatterns += [
        path('profile/', profile.detail_view, name='profile-detail'),
        path('profile/delete/', profile.delete_view, name='profile-delete'),
    ]

urlpatterns += [
    path('profile/deactivated/', group.group_list_mine_deactivated, name='deactivated-groups'),
    path(
        'profile/activate/<int:group_id>/',
        group.activate_or_deactivate,
        name='group-activate',
        kwargs={'activate': True},
    ),
    path(
        'profile/deactivate/<int:group_id>/',
        group.activate_or_deactivate,
        name='group-deactivate',
        kwargs={'activate': False},
    ),
]

# in SSO-portals we redirect the signup page to the login page
if is_sso_portal():
    urlpatterns += [
        path('signup/', RedirectView.as_view(url=reverse_lazy('login'), permanent=False)),
    ]

if settings.COSINNUS_FACEBOOK_INTEGRATION_ENABLED:
    urlpatterns += [
        path(
            'fb-integration/save-auth-tokens/', facebook_integration.save_auth_tokens, name='facebook-save-auth-tokens'
        ),
        path(
            'fb-integration/remove-facebook/',
            facebook_integration.remove_facebook_association,
            name='facebook-remove-association',
        ),
        path(
            'fb-integration/confirm-page-admin/<int:group_id>/',
            facebook_integration.confirm_page_admin,
            name='facebook-confirm-page-admin',
        ),
    ]

if settings.COSINNUS_IDEAS_ENABLED:
    urlpatterns += [
        path('ideas/', map.tile_view, name='idea-list', kwargs={'types': ['ideas']}),
        path('ideas/mine/', map.tile_view, name='idea-list-mine', kwargs={'types': ['ideas'], 'show_mine': True}),
        path('ideas/add/', idea.idea_create, name='idea-create'),
        path('ideas/<slug:slug>/edit/', idea.idea_edit, name='idea-edit'),
        path('ideas/<slug:slug>/delete/', idea.idea_delete, name='idea-delete'),
    ]

if settings.COSINNUS_CUSTOM_PREMIUM_PAGE_ENABLED:
    urlpatterns += [
        path(
            'portal/supporters/', TemplateView.as_view(template_name='premium_info_page.html'), name='premium-info-page'
        ),
    ]

for url_key in group_model_registry:
    plural_url_key = group_model_registry.get_plural_url_key(url_key, url_key + '_s')
    prefix = group_model_registry.get_url_name_prefix(url_key, '')

    urlpatterns += [
        path(
            f'{plural_url_key}/in-group-with/<str:group>/',
            group.group_list_filtered,
            name=prefix + 'group-list-filtered',
        ),
        path(f'{plural_url_key}/invited/', group.group_list_invited, name=prefix + 'group-list-invited'),
        # path(f'{plural_url_key}/map/', group.group_list_map', name=prefix+'group-list-map'),
        path(f'{plural_url_key}/add/', group.group_create, name=prefix + 'group-add'),
        path(f'{url_key}/<str:group>/', group.group_startpage, name=prefix + 'group-dashboard'),
        path(f'{url_key}/<str:group>/microsite/', microsite.group_microsite_view, name=prefix + 'group-microsite'),
        # path(f'{url_key}/<str:group>/_microsite__old_/', 'cms.group_microsite', name=prefix+'group-microsite'),
        # path(
        #   f'{url_key}/<str:group>/_microsite__old_/edit/', 'cms.group_microsite_edit',
        #   name=prefix+'group-microsite-edit'
        # ),
        path(f'{url_key}/<str:group>/meeting/', group.group_meeting, name=prefix + 'group-meeting'),
        path(f'{url_key}/<str:group>/members/', group.group_detail, name=prefix + 'group-detail'),
        path(f'{url_key}/<str:group>/members/recruit/', group.group_user_recruit, name=prefix + 'group-user-recruit'),
        path(
            f'{url_key}/<str:group>/members/recruitdelete/<int:id>/',
            group.group_user_recruit_delete,
            name=prefix + 'group-user-recruit-delete',
        ),
        # path(f'{url_key}/<str:group>/members/map/', group.group_members_map', name=prefix+'group-members-map'),
        path(f'{url_key}/<str:group>/edit/', group.group_update, name=prefix + 'group-edit'),
        path(f'{url_key}/<str:group>/delete/', group.group_delete, name=prefix + 'group-delete'),
        path(f'{url_key}/<str:group>/join/', group.group_user_join, name=prefix + 'group-user-join'),
        path(
            f'{url_key}/<str:group>/auto-join/',
            group.group_user_join_csrf_exempt,
            name=prefix + 'group-user-join-nocsrf',
        ),
        path(f'{url_key}/<str:group>/leave/', group.group_user_leave, name=prefix + 'group-user-leave'),
        path(f'{url_key}/<str:group>/withdraw/', group.group_user_withdraw, name=prefix + 'group-user-withdraw'),
        path(
            f'{url_key}/<str:group>/decline/', group.group_user_invitation_decline, name=prefix + 'group-user-decline'
        ),
        path(f'{url_key}/<str:group>/accept/', group.group_user_invitation_accept, name=prefix + 'group-user-accept'),
        path(f'{url_key}/<str:group>/activate-app/', group.group_activate_app, name=prefix + 'group-activate-app'),
        path(f'{url_key}/<str:group>/organizations/', group.group_organizations, name=prefix + 'group-organizations'),
        path(
            f'{url_key}/<str:group>/organizations/request/',
            group.group_organization_request,
            name=prefix + 'group-organization-request',
        ),
        path(
            f'{url_key}/<str:group>/organizations/organization-request-select2/',
            group.group_organization_request_select2,
            name=prefix + 'group-organization-request-select2',
        ),
        path(f'{url_key}/<str:group>/users/', group.group_user_list, name=prefix + 'group-user-list'),
        # Deprecated
        # path(f'{url_key}/<str:group>/users/add/', group.group_user_add, name=prefix + 'group-user-add-generic'),
        path(
            f'{url_key}/<str:group>/users/add-multiple/',
            group.group_user_add_multiple,
            name=prefix + 'group-user-add-multiple',
        ),
        path(f'{url_key}/<str:group>/add-multiple/', group.group_add_multiple, name=prefix + 'group-add-multiple'),
        path(f'{url_key}/<str:group>/users/add/<str:username>/', group.group_user_add, name=prefix + 'group-user-add'),
        path(
            f'{url_key}/<str:group>/users/delete/<str:username>/',
            group.group_user_delete,
            name=prefix + 'group-user-delete',
        ),
        path(
            f'{url_key}/<str:group>/users/edit/<str:username>/',
            group.group_user_update,
            name=prefix + 'group-user-edit',
        ),
        path(
            f'{url_key}/<str:group>/users/member-invite-select2/',
            group.user_group_member_invite_select2,
            name=prefix + 'group-member-invite-select2',
        ),
        path(
            f'{url_key}/<str:group>/group-invite-select2/',
            group.group_invite_select2,
            name=prefix + 'group-invite-select2',
        ),
        path(
            f'{url_key}/<str:group>/group-group-invite-delete/',
            group.group_group_invite_delete,
            name=prefix + 'group-group-invite-delete',
        ),
        path(f'{url_key}/<str:group>/export/', group.group_export, name=prefix + 'group-export'),
        path(f'{url_key}/<str:group>/widgets/add/', widget.widget_add_group, name=prefix + 'widget-add-group-empty'),
        path(
            f'{url_key}/<str:group>/widgets/add/<str:app_name>/<str:widget_name>/',
            widget.widget_add_group,
            name=prefix + 'widget-add-group',
        ),
        path(
            f'{url_key}/<str:group>/reflectedassign/',
            group.group_assign_reflected_object,
            name=prefix + 'group-assign-reflected',
        ),
        path(
            f'{url_key}/<str:group>/attachmentselect/<str:model>',
            attached_object.attachable_object_select2_view,
            name=prefix + 'attached_object_select2_view',
        ),
    ]
    if settings.COSINNUS_MITWIRKOMAT_INTEGRATION_ENABLED:
        urlpatterns += [
            path(
                f'{url_key}/<str:group>/matching_settings/',
                mitwirkomat.mitwirkomat_settings_view,
                name=prefix + 'mitwirkomat-settings',
            ),
        ]

urlpatterns += url_registry.urlpatterns

# URLs for API version 2
router = routers.SimpleRouter()

router.register(r'public_conferences', PublicConferenceViewSet, basename='public_conference')
router.register(r'conferences', ConferenceViewSet, basename='conference')
router.register(r'groups', CosinnusSocietyViewSet, basename='group')
router.register(r'exchange/groups', CosinnusSocietyExchangeViewSet, basename='group_exchange')
router.register(r'projects', CosinnusProjectViewSet, basename='project')
router.register(r'exchange/projects', CosinnusProjectExchangeViewSet, basename='project_exchange')
router.register(r'organizations', OrganizationViewSet, basename='organization')

# imports from external projects at this time may fail in certain test environments
try:
    from cosinnus_event.api.views import EventExchangeViewSet, EventViewSet

    router.register(r'events', EventViewSet, basename='event')
    router.register(r'exchange/events', EventExchangeViewSet, basename='event_exchange')
except Exception:
    pass
# imports from external projects at this time may fail in certain test environments
try:
    from cosinnus_note.api.views import NoteViewSet

    router.register(r'notes', NoteViewSet, basename='note')
except Exception:
    pass

if getattr(settings, 'COSINNUS_API_SETTINGS', {}).get('user'):
    router.register(r'users', UserViewSet, basename='user')

if settings.COSINNUS_ROCKET_EXPORT_ENABLED:
    # imports from external projects at this time may fail in certain test environments
    try:
        from cosinnus_message.api.views import MessageExportView

        urlpatterns += [
            path('api/v2/rocket-export/', MessageExportView.as_view()),
        ]
    except Exception:
        pass

# Firebase fcm-django urls
if settings.COSINNUS_FIREBASE_ENABLED:
    from fcm_django.api.rest_framework import FCMDeviceAuthorizedViewSet

    router.register('devices', FCMDeviceAuthorizedViewSet)
    urlpatterns += [
        # URLs will show up at <api_root>/devices
        # DRF browsable API which lists all available endpoints
        path('fcm/', include(router.urls)),
    ]

if settings.COSINNUS_V3_FRONTEND_ENABLED:
    # frontend only URLs. these URLs do not have real views, because the frontend server will catch the paths
    # and serve a different page
    urlpatterns += [
        path(
            'setup/profile/',
            TemplateView.as_view(template_name='premium_info_page.html'),
            name='v3-frontend-setup-profile',
        ),
    ]

if getattr(settings, 'COSINNUS_EMPTY_FILE_DOWNLOAD_NAME', None):
    urlpatterns += [
        path(f'{settings.COSINNUS_EMPTY_FILE_DOWNLOAD_NAME}', common.empty_file_download),
    ]

urlpatterns += [
    path('o/me/', oauth_current_user),
    path('o/user/', oauth_user),
    path('o/profile/', oauth_profile),
]


api_v2_url_patterns = [
    path('api/v2/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v2/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v2/current_user/', current_user, name='api-current-user'),
    path('api/v2/settings/', api_settings, name='api-settings'),
    path('api/v2/config/', api_config, name='api-config'),
    path('api/v2/statistics/', api_statistics, name='api-statistics'),
    path('api/v2/jsi18n/', translations, name='api-jsi18n'),
    path('api/v2/', include((router.urls, 'api'), namespace='api')),
]
api_v3_url_patterns = [
    path('', include(('cosinnus.urls_api_frontend', 'cosinnus'), namespace='frontend-api')),
]

schema_url_patterns = api_v2_url_patterns + api_v3_url_patterns
urlpatterns += schema_url_patterns


class StrictProductionHttpsSchemaGenerator(OpenAPISchemaGenerator):
    """Strictly sets "https" as schema in non-DEBUG environments"""

    def get_schema(self, request=None, public=False):
        schema = super().get_schema(request, public)
        if settings.DEBUG:
            schema.schemes = ['http', 'https']
        else:
            schema.schemes = [
                'https',
            ]
        return schema


schema_view = get_schema_view(
    openapi.Info(
        title='WECHANGE API',
        default_version='v2',
        description='WECHANGE API (in progress)',
        terms_of_service='https://wechange.de/cms/nutzungsbedingungen/',
        contact=openapi.Contact(email='support@wechange.de'),
        license=openapi.License(name='AGPL 3.0'),
    ),
    generator_class=StrictProductionHttpsSchemaGenerator,
    public=True,
    permission_classes=(permissions.AllowAny,),
    patterns=schema_url_patterns,
)

urlpatterns += [
    re_path(r'api/v2/(?:header|navbar)/$', header, name='api-header'),
    path('api/v2/footer/', footer, name='api-footer'),
    re_path(r'swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    path('api/v2/docs/', RedirectView.as_view(url='/swagger/', permanent=False)),
]


if getattr(settings, 'TESTING', False):
    from cosinnus.tests.view_tests.views import main_content_form_test_view, main_content_test_view

    urlpatterns += [
        path('test/main-content-test-view/', main_content_test_view, name='main-content-test'),
        path('test/main-content-form-test-view/', main_content_form_test_view, name='main-content-form-test'),
    ]
