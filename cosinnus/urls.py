# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import include, url
from django.urls import reverse_lazy, re_path
from django.views.generic.base import RedirectView, TemplateView
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import routers, permissions
from rest_framework_jwt.views import obtain_jwt_token, refresh_jwt_token
import two_factor.views as two_factor_views

from cosinnus.api.views.group import CosinnusSocietyViewSet, CosinnusProjectViewSet
from cosinnus.api.views.i18n import translations
from cosinnus.api.views.portal import statistics as api_statistics, header, footer, settings as api_settings
from cosinnus.api.views.user import oauth_user, oauth_profile, current_user, oauth_current_user, UserViewSet
from cosinnus.conf import settings
from cosinnus.core.registries import url_registry
from cosinnus.core.registries.group_models import group_model_registry
from cosinnus.templatetags.cosinnus_tags import is_integrated_portal, is_sso_portal
from cosinnus.views import bbb_room, user_import, user_match
from cosinnus.views import map, map_api, user, profile, common, widget, search, feedback, group, \
    statistics, housekeeping, facebook_integration, microsite, idea, attached_object, authentication, \
    user_dashboard, ui_prefs, administration, user_dashboard_announcement, dynamic_fields, \
    conference_administration
from cosinnus_conference.api.views import ConferenceViewSet, \
    PublicConferenceViewSet
from cosinnus_organization.api.views import OrganizationViewSet


app_name = 'cosinnus'

urlpatterns = [
    # we do not define an index anymore and let CMS handle that.

    url(r'^users/$', map.tile_view, name='user-list', kwargs={'types': ['people']}),
    
    url(r'^portal/admins/$', user.portal_admin_list, name='portal-admin-list'),
    url(r'^user/(?P<username>[^/]+)/$', profile.detail_view, name='profile-detail'),
    
    url(r'^language/(?P<language>[^/]+)/$', common.switch_language, name='switch-language'),
    
    url(r'^widgets/list/$', widget.widget_list, name='widget-list'),
    url(r'^widgets/add/user/$', widget.widget_add_user, name='widget-add-user-empty'),
    url(r'^widgets/add/user/(?P<app_name>[^/]+)/(?P<widget_name>[^/]+)/$', widget.widget_add_user, name='widget-add-user'),
    url(r'^widgets/save/$', widget.save_widget_config, name='widget-save-config'),
    url(r'^widget/(?P<id>\d+)/$', widget.widget_detail, name='widget-detail'),
    url(r'^widget/(?P<id>\d+)/(?P<offset>\d+)/$', widget.widget_detail, name='widget-detail-offset'),
    url(r'^widget/(?P<id>\d+)/delete/$', widget.widget_delete, name='widget-delete'),
    url(r'^widget/(?P<id>\d+)/edit/$', widget.widget_edit, name='widget-edit'),
    url(r'^widget/(?P<id>\d+)/edit/(?P<app_name>[^/]+)/(?P<widget_name>[^/]+)/$', widget.widget_edit, name='widget-edit-swap'),

    url(r'^search/$', search.search, name='search'),
    
    url(r'^map/$', map.map_view, name='map'),
    
    url(r'^projects/$', map.tile_view, name='group-list', kwargs={'types': ['projects']}),
    url(r'^groups/$', map.tile_view, name='group__group-list', kwargs={'types': ['groups']}),
    url(r'^conferences/$', map.tile_view, name='conference__group-list', kwargs={'types': ['conferences']}),
    url(r'^projects/mine/$', map.tile_view, name='group-list-mine', kwargs={'types': ['projects'], 'show_mine': True}),
    url(r'^groups/mine/$', map.tile_view, name='group__group-list-mine', kwargs={'types': ['groups'], 'show_mine': True}),
    
    url(r'^map/embed/$', map.map_embed_view, name='map-embed'),
    url(r'^map/search/$', map_api.map_search_endpoint, name='map-search-endpoint'),
    url(r'^map/search/(?P<filter_group_id>\d+)/$', map_api.map_search_endpoint, name='map-search-endpoint-filtered'),
    url(r'^map/detail/$', map_api.map_detail_endpoint, name='map-detail-endpoint'),
    
    url(r'^likefollowstar/$', common.do_likefollowstar,  name='likefollowstar-view'),
    
    url(r'^bbb/room/(?P<room_id>\d+)/$', bbb_room.bbb_room_meeting, name='bbb-room'),
    url(r'^bbb/queue/(?P<mt_id>\d+)/$', bbb_room.bbb_room_meeting_queue, name='bbb-room-queue'),
    url(r'^bbb/queue-api/(?P<mt_id>\d+)/$', bbb_room.bbb_room_meeting_queue_api, name='bbb-room-queue-api'),
    
    url(r'^invitations/$', group.group_list_invited, name='invitations', kwargs={'show_all': True}),
    url(r'^welcome/$', user.welcome_settings, name='welcome-settings'),
    url(r'^join/$', user.group_invite_token_enter_view, name='group-invite-token-enter'),
    url(r'^join/(?P<token>[^/]+)/$', user.group_invite_token_view, name='group-invite-token'),
    
    url(r'^account/report/$', feedback.report_object, name='report-object'),
    url(r'^account/accept_tos/$', user.accept_tos, name='accept-tos'),
    url(r'^account/resend_email_validation/$', user.resend_email_validation, name='resend-email-validation'),
    url(r'^account/accept_updated_tos/$', user.accept_updated_tos, name='accept-updated-tos'),
    url(r'^account/list-unsubscribe/(?P<email>[^/]+)/(?P<token>[^/]+)/$', user.add_email_to_blacklist, name='user-add-email-blacklist'),
    url(r'^account/list-unsubscribe-result/$', user.add_email_to_blacklist_result, name='user-add-email-blacklist-result'),
    url(r'^account/deactivated/$', group.group_list_mine_deactivated, name='deactivated-groups'),
    url(r'^account/activate/(?P<group_id>\d+)/$', group.activate_or_deactivate, name='group-activate', kwargs={'activate': True}),
    url(r'^account/deactivate/(?P<group_id>\d+)/$', group.activate_or_deactivate, name='group-deactivate', kwargs={'activate': False}),
    url(r'^account/verify_email/(?P<email_verification_param>[^/]+)/$', user.verifiy_user_email, name='user-verifiy-email'),
    
    # --- DEPERECATED -----
    # these URL paths are deprecated and have been replaced by the /account/ prefix
    # they should be kept until mid-2021 so old sent-out emails do not point to a 404
    url(r'^administration/list-unsubscribe/(?P<email>[^/]+)/(?P<token>[^/]+)/$', user.add_email_to_blacklist, name='OLD-user-add-email-blacklist'),
    url(r'^administration/list-unsubscribe-result/$', user.add_email_to_blacklist_result, name='OLD-user-add-email-blacklist-result'),
    url(r'^administration/deactivated/$', group.group_list_mine_deactivated, name='OLD-deactivated-groups'),
    url(r'^administration/activate/(?P<group_id>\d+)/$', group.activate_or_deactivate, name='OLD-group-activate', kwargs={'activate': True}),
    url(r'^administration/deactivate/(?P<group_id>\d+)/$', group.activate_or_deactivate, name='OLD-group-deactivate', kwargs={'activate': False}),
    url(r'^administration/verify_email/(?P<email_verification_param>[^/]+)/$', user.verifiy_user_email, name='OLD-user-verifiy-email'),
    # ---- END DEPRECATED ---
    
    # these URLs belong to the frontend administration area for superusers
    url(r'^administration/$', administration.administration, name='administration'),
    url(r'^administration/login-2fa/$', authentication.admin_only_otp_token_validation, name='login-2fa'),
    url(r'^administration/approve_user/(?P<user_id>\d+)/$', user.approve_user, name='user-approve'),
    url(r'^administration/deny_user/(?P<user_id>\d+)/$', user.deny_user, name='user-deny'),
    
    url(r'^administration/welcome_email/$', administration.welcome_email_edit, name='administration-welcome-email'),

    url(r'^administration/users/$', administration.user_list, name='administration-users'),
    url(r'^administration/users/add/$', administration.user_add, name='administration-user-create'),
    
    url(r'^administration/group_newsletter/$', administration.groups_newsletters, name='administration-groups-newsletter'),
    url(r'^administration/group_newsletter/add/$', administration.groups_newsletter_create, name='administration-groups-newsletter-create'),
    url(r'^administration/group_newsletter/(?P<newsletter_id>\d+)/edit/$', administration.groups_newsletter_update, name='administration-groups-newsletter-update'),
    url(r'^administration/tag_newsletter/$', administration.managed_tags_newsletters, name='administration-managed-tags-newsletter'),
    url(r'^administration/tag_newsletter/add/$', administration.managed_tags_newsletter_create, name='administration-managed-tags-newsletter-create'),
    url(r'^administration/tag_newsletter/(?P<newsletter_id>\d+)/edit/$', administration.managed_tags_newsletter_update, name='administration-managed-tags-newsletter-update'),

    url(r'^administration/announcements/$', user_dashboard_announcement.list_view, name='user-dashboard-announcement-list'),
    url(r'^administration/announcements/add/$', user_dashboard_announcement.user_dashboard_announcement_create, name='user-dashboard-announcement-create'),
    url(r'^administration/announcement/(?P<slug>[^/]+)/edit/$', user_dashboard_announcement.user_dashboard_announcement_edit, name='user-dashboard-announcement-edit'),
    url(r'^administration/announcement/(?P<slug>[^/]+)/delete/$', user_dashboard_announcement.user_dashboard_announcement_delete, name='user-dashboard-announcement-delete'),
    url(r'^administration/announcement/(?P<slug>[^/]+)/activate-toggle/$', user_dashboard_announcement.user_dashboard_announcement_activate, name='user-dashboard-announcement-activate'),
    
    url(r'^conference_administration/$', conference_administration.conference_administration, name='conference-administration'),
    url(r'^administration/conference_overview/$', conference_administration.conference_overview, name='conference-administration-overview'),
    url(r'^administration/conference_overview/nonstandard/$', conference_administration.conference_overview, name='conference-administration-overview-nonstandard', kwargs={'only_nonstandard': True}),
    url(r'^administration/conference_overview/premium/$', conference_administration.conference_overview, name='conference-administration-overview-premium', kwargs={'only_premium': True}),
    url(r'^administration/conference/(?P<slug>[^/]+)/blocks/add/$', conference_administration.conference_add_premium_block, name='conference-administration-add-premium-block'),
    url(r'^administration/conference/block/(?P<block_id>\d+)/edit/$', conference_administration.conference_edit_premium_block, name='conference-administration-edit-premium-block'),
    
    url(r'^statistics/simple/$', statistics.simple_statistics, name='simple-statistics'),
    
    url(r'^housekeeping/ensure_group_widgets/$', housekeeping.ensure_group_widgets, name='housekeeping-ensure-group-widgets'),
    url(r'^housekeeping/newsletterusers/$', housekeeping.newsletter_users, name='housekeeping-newsletter-user-emails'),
    url(r'^housekeeping/activeuseremails/$', housekeeping.active_user_emails, name='housekeeping-active-user-emails'),
    url(r'^housekeeping/neverloggedinuseremails/$', housekeeping.never_logged_in_user_emails, name='housekeeping-never-logged-in-user-emails'),
    url(r'^housekeeping/deletespamusers/$', housekeeping.delete_spam_users, name='housekeeping_delete_spam_users'),
    url(r'^housekeeping/movegroupcontent/(?P<fromgroup>[^/]+)/(?P<togroup>[^/]+)/$', housekeeping.move_group_content, name='housekeeping_move_group_content'),
    url(r'^housekeeping/recreategroupwidgets/$', housekeeping.recreate_all_group_widgets, name='housekeeping_recreate_all_group_widgets'),
    url(r'^housekeeping/setcache/(?P<content>[^/]+)/$', housekeeping.setcache, name='housekeeping-setcache'),
    url(r'^housekeeping/fillcache/(?P<number>[^/]+)/$', housekeeping.fillcache, name='housekeeping-fillcache'),
    url(r'^housekeeping/getcache$', housekeeping.getcache, name='housekeeping-getcache'),
    url(r'^housekeeping/deletecache$', housekeeping.deletecache, name='housekeeping-deletecache'),
    url(r'^housekeeping/test_logging/$', housekeeping.test_logging, name='housekeeping-test-logging'),
    url(r'^housekeeping/test_logging/info/$', housekeeping.test_logging, name='housekeeping-test-logging', kwargs={'level': 'info'}),
    url(r'^housekeeping/test_logging/warning/$', housekeeping.test_logging, name='housekeeping-test-logging', kwargs={'level': 'warning'}),
    url(r'^housekeeping/test_logging/error/$', housekeeping.test_logging, name='housekeeping-test-logging', kwargs={'level': 'error'}),
    url(r'^housekeeping/test_logging/exception/$', housekeeping.test_logging, name='housekeeping-test-logging', kwargs={'level': 'exception'}),
    url(r'^housekeeping/validate_redirects/', housekeeping.check_and_delete_loop_redirects, name='housekeeping-validate-redirects'),
    url(r'^housekeeping/add_members_to_forum/', housekeeping.add_members_to_forum, name='housekeeping-add-members-to-forum'),
    url(r'^housekeeping/user_statistics/', housekeeping.user_statistics, name='housekeeping-user-statistics'),
    url(r'^housekeeping/create_map_test_entities/(?P<count>\d+)/', housekeeping.create_map_test_entities, name='housekeeping-create-map-test-entities'),
    url(r'^housekeeping/reset_user_tos_flags/', housekeeping.reset_user_tos_flags, name='housekeeping-reset-user-tos-flags'),
    url(r'^housekeeping/send_testmail/', housekeeping.send_testmail, name='housekeeping-send-testmail'),
    url(r'^housekeeping/print_testmail/', housekeeping.print_testmail, name='housekeeping-print-testmail'),
    url(r'^housekeeping/print_testdigest/', housekeeping.print_testdigest, name='housekeeping-print-testdigest'),
    url(r'^housekeeping/print_settings/', housekeeping.print_settings, name='housekeeping-print-settings'),
    url(r'^housekeeping/conf_settings_info/', housekeeping.portal_switches_and_settings, name='housekeeping-portal-switches-and-settings'),
    url(r'^housekeeping/group_admin_emails/(?P<slugs>[^/]+)/', housekeeping.group_admin_emails, name='housekeeping-group-admin-emails'),
    
    url(r'^error/$', common.generic_error_page_view, name='generic-error-page'),

    url(r'^select2/', include(('cosinnus.urls_select2', 'select2'), namespace='select2')),
]

if getattr(settings, 'COSINNUS_USER_IMPORT_ADMINISTRATION_VIEWS_ENABLED', False):
    urlpatterns += [
        url(r'^administration/user_import/$', user_import.user_import_view, name='administration-user-import'),
        url(r'^administration/user_import/archived/$', user_import.archived_user_import_list_view, name='administration-archived-user-import-list'),
        url(r'^administration/user_import/archived/(?P<pk>\d+)/$', user_import.archived_user_import_detail_view, name='administration-archived-user-import-detail'),
        url(r'^administration/user_import/archived/(?P<pk>\d+)/delete/$', user_import.archived_user_import_delete_view, name='administration-archived-user-import-delete'),
    
    ]

if getattr(settings, 'COSINNUS_DYNAMIC_FIELD_ADMINISTRATION_VIEWS_ENABLED', False): 
    urlpatterns += [
        url(r'^administration/admin_dynamic_fields/edit/$', dynamic_fields.dynamic_field_admin_choices_form_view, name='administration-dynamic-fields'),
    ]

if getattr(settings, 'COSINNUS_PLATFORM_ADMIN_CAN_EDIT_PROFILES', False):
    urlpatterns += [
        url(r'^administration/users/(?P<pk>\d+)/edit/$', administration.user_update, name='administration-user-update'),
    ]

if getattr(settings, 'COSINNUS_USE_V2_DASHBOARD', False) or getattr(settings, 'COSINNUS_USE_V2_DASHBOARD_ADMIN_ONLY', False):
    dashboard_url = getattr(settings, 'COSINNUS_V2_DASHBOARD_URL_FRAGMENT', 'dashboard')
    if getattr(settings, 'COSINNUS_CLOUD_ENABLED', False):
        import cosinnus_cloud.views as cosinnus_cloud_views # noqa
        urlpatterns += [
            url(fr'^dashboard/api/user_typed_content/cloud_files/$', cosinnus_cloud_views.api_user_cloud_files_content, name='user-dashboard-api-typed-content-cloud'),
            url(r'^dashboard/api/user_typed_content/recent/cloud_files/$', cosinnus_cloud_views.api_user_cloud_files_content, name='user-dashboard-api-typed-content-cloud', kwargs={'show_recent':True}),
            url(r'^search/cloudfiles/$', map.tile_view, name='cloudfiles-search', kwargs={'types': ['cloudfiles']}),
        ]
    urlpatterns += [
        url(fr'^{dashboard_url}/$', user_dashboard.user_dashboard_view, name='user-dashboard'),
        url(r'^dashboard/api/user_groups/$', user_dashboard.api_user_groups, name='user-dashboard-api-groups'),
        url(r'^dashboard/api/user_liked_ideas/$', user_dashboard.api_user_liked_ideas, name='user-dashboard-api-liked-ideas'),
        url(r'^dashboard/api/user_starred_users/$', user_dashboard.api_user_starred_users, name='user-dashboard-api-starred-users'),
        url(r'^dashboard/api/user_starred_objects/$', user_dashboard.api_user_starred_objects, name='user-dashboard-api-starred-objects'),
        url(r'^dashboard/api/user_followed_objects/$', user_dashboard.api_user_followed_objects, name='user-dashboard-api-followed-objects'),
        url(r'^dashboard/api/user_typed_content/(?P<content>[^/]+)/$', user_dashboard.api_user_typed_content, name='user-dashboard-api-typed-content'),
        url(r'^dashboard/api/user_typed_content/recent/(?P<content>[^/]+)/$', user_dashboard.api_user_typed_content, name='user-dashboard-api-typed-content', kwargs={'show_recent':True}),
        url(r'^dashboard/api/timeline/(?P<content>[^/]+)/$', user_dashboard.api_timeline, name='user-dashboard-api-timeline-filtered'),
        url(r'^dashboard/api/timeline/$', user_dashboard.api_timeline, name='user-dashboard-api-timeline'),
        url(r'^dashboard/api/save_ui_prefs/$', ui_prefs.api_ui_prefs, name='user-dashboard-api-ui-prefs'),
    ]

if getattr(settings, 'COSINNUS_USE_V2_NAVBAR', False) or getattr(settings, 'COSINNUS_USE_V2_NAVBAR_ADMIN_ONLY', False):
    urlpatterns += [
        url(r'^search/api/quicksearch/$', search.api_quicksearch, name='quicksearch-api'),
    ]

if getattr(settings, 'COSINNUS_ENABLE_USER_MATCH', True):
    urlpatterns += [
        url(r'^user_match/$', user_match.user_match_list_view, name='user-match'),
        url(r'^user_match_assign/$', user_match.match_create_view, name='user-match-match'),
    ]

if settings.COSINNUS_USER_2_FACTOR_AUTH_ENABLED:
    urlpatterns += [
        url(r'^two_factor_auth/token_login/$', authentication.user_otp_token_validation, name='two-factor-auth-token'),
        url(r'^two_factor_auth/token_login/backup/$', authentication.user_otp_token_validation, name='two-factor-auth-token-backup', kwargs={'two_factor_method': 'backup'}),
        url(r'^two_factor_auth/qrcode/$', authentication.two_factor_auth_qr, name='two-factor-auth-qr'),
        url(r'^two_factor_auth/settings/$', authentication.two_factor_user_hub, name='two-factor-auth-settings'),
        url(r'^two_factor_auth/settings/setup/$', authentication.two_factor_auth_setup, name='two-factor-auth-setup'),
        url(r'^two_factor_auth/settings/setup/complete/$', authentication.two_factor_auth_setup_complete, name='two-factor-auth-setup-complete'),
        url(r'^two_factor_auth/settings/disable/$', authentication.two_factor_auth_disable, name='two-factor-auth-disable'),
        url(r'^two_factor_auth/settings/backup_tokens/$', authentication.two_factor_auth_back_tokens, name='two-factor-auth-backup-tokens'),
    ]

# some user management not allowed in integrated mode and sso-mode
if not is_integrated_portal() and not is_sso_portal():
    urlpatterns += [
        url(r'^profile/edit/$', profile.update_view, name='profile-edit'),
        url(r'^signup/$', user.user_create, name='user-add'),
    ]

# some more user management not allowed in integrated mode
if not is_integrated_portal():
    urlpatterns += [
        url(r'^profile/$', profile.detail_view, name='profile-detail'),
        url(r'^profile/delete/$', profile.delete_view, name='profile-delete'),
    ]

# in SSO-portals we redirect the signup page to the login page
if is_sso_portal():
    urlpatterns += [
        url(r'^signup/$', RedirectView.as_view(url=reverse_lazy('login'), permanent=False)),
    ]
    
if settings.COSINNUS_FACEBOOK_INTEGRATION_ENABLED:
    urlpatterns += [
        url(r'^fb-integration/save-auth-tokens/$', facebook_integration.save_auth_tokens,  name='facebook-save-auth-tokens'),
        url(r'^fb-integration/remove-facebook/$', facebook_integration.remove_facebook_association,  name='facebook-remove-association'),
        url(r'^fb-integration/confirm-page-admin/(?P<group_id>\d+)/$', facebook_integration.confirm_page_admin,  name='facebook-confirm-page-admin'),
    ]

if settings.COSINNUS_IDEAS_ENABLED:
    urlpatterns += [
        url(r'^ideas/$', map.tile_view, name='idea-list', kwargs={'types': ['ideas']}),
        url(r'^ideas/mine/$', map.tile_view, name='idea-list-mine', kwargs={'types': ['ideas'], 'show_mine': True}),
        url(r'^ideas/add/$', idea.idea_create, name='idea-create'),
        url(r'^ideas/(?P<slug>[^/]+)/edit/$', idea.idea_edit, name='idea-edit'),
        url(r'^ideas/(?P<slug>[^/]+)/delete/$', idea.idea_delete, name='idea-delete'),
    ]

if settings.COSINNUS_CUSTOM_PREMIUM_PAGE_ENABLED:
    urlpatterns += [
        url(r'^portal/supporters/$', TemplateView.as_view(template_name='premium_info_page.html'), name='premium-info-page'),
    ]

for url_key in group_model_registry:
    plural_url_key = group_model_registry.get_plural_url_key(url_key, url_key + '_s')
    prefix = group_model_registry.get_url_name_prefix(url_key, '')
    
    urlpatterns += [
        url(r'^%s/in-group-with/(?P<group>[^/]+)/$' % plural_url_key, group.group_list_filtered, name=prefix+'group-list-filtered'),
        url(r'^%s/invited/$' % plural_url_key, group.group_list_invited, name=prefix+'group-list-invited'),
        #url(r'^%s/map/$' % plural_url_key, group.group_list_map', name=prefix+'group-list-map'),
        url(r'^%s/add/$' % plural_url_key, group.group_create, name=prefix+'group-add'),
        url(r'^%s/(?P<group>[^/]+)/$' % url_key, group.group_startpage, name=prefix+'group-dashboard'),
        url(r'^%s/(?P<group>[^/]+)/microsite/$' % url_key, microsite.group_microsite_view, name=prefix+'group-microsite'),
        #url(r'^%s/(?P<group>[^/]+)/_microsite__old_/$' % url_key, 'cms.group_microsite', name=prefix+'group-microsite'),
        #url(r'^%s/(?P<group>[^/]+)/_microsite__old_/edit/$' % url_key, 'cms.group_microsite_edit', name=prefix+'group-microsite-edit'),
        url(r'^%s/(?P<group>[^/]+)/meeting/$' % url_key, group.group_meeting, name=prefix+'group-meeting'),
        url(r'^%s/(?P<group>[^/]+)/members/$' % url_key, group.group_detail, name=prefix+'group-detail'),
        url(r'^%s/(?P<group>[^/]+)/members/recruit/$' % url_key, group.group_user_recruit, name=prefix+'group-user-recruit'),
        url(r'^%s/(?P<group>[^/]+)/members/recruitdelete/(?P<id>\d+)/$' % url_key, group.group_user_recruit_delete, name=prefix+'group-user-recruit-delete'),
        #url(r'^%s/(?P<group>[^/]+)/members/map/$' % url_key, group.group_members_map', name=prefix+'group-members-map'),
        url(r'^%s/(?P<group>[^/]+)/edit/$' % url_key, group.group_update, name=prefix+'group-edit'),
        url(r'^%s/(?P<group>[^/]+)/delete/$' % url_key, group.group_delete, name=prefix+'group-delete'),
        url(r'^%s/(?P<group>[^/]+)/join/$' % url_key, group.group_user_join, name=prefix+'group-user-join'),
        url(r'^%s/(?P<group>[^/]+)/auto-join/$' % url_key, group.group_user_join_csrf_exempt, name=prefix+'group-user-join-nocsrf'),
        url(r'^%s/(?P<group>[^/]+)/leave/$' % url_key, group.group_user_leave, name=prefix+'group-user-leave'),
        url(r'^%s/(?P<group>[^/]+)/withdraw/$' % url_key, group.group_user_withdraw, name=prefix+'group-user-withdraw'),
        url(r'^%s/(?P<group>[^/]+)/decline/$' % url_key, group.group_user_invitation_decline, name=prefix+'group-user-decline'),
        url(r'^%s/(?P<group>[^/]+)/accept/$' % url_key, group.group_user_invitation_accept, name=prefix+'group-user-accept'),
        url(r'^%s/(?P<group>[^/]+)/activate-app/$' % url_key, group.group_activate_app, name=prefix+'group-activate-app'),
        url(r'^%s/(?P<group>[^/]+)/organizations/$' % url_key, group.group_organizations, name=prefix+'group-organizations'),
        url(r'^%s/(?P<group>[^/]+)/organizations/request/$' % url_key, group.group_organization_request, name=prefix+'group-organization-request'),
        url(r'^%s/(?P<group>[^/]+)/organizations/organization-request-select2/$' % url_key, group.group_organization_request_select2, name=prefix+'group-organization-request-select2'),

        url(r'^%s/(?P<group>[^/]+)/users/$' % url_key, group.group_user_list, name=prefix+'group-user-list'),
        url(r'^%s/(?P<group>[^/]+)/users/add/$' % url_key, group.group_user_add, name=prefix+'group-user-add-generic'),
        url(r'^%s/(?P<group>[^/]+)/users/add-multiple/$' % url_key, group.group_user_add_multiple, name=prefix+'group-user-add-multiple'),
        url(r'^%s/(?P<group>[^/]+)/add-multiple/$' % url_key, group.group_add_multiple, name=prefix+'group-add-multiple'),
        url(r'^%s/(?P<group>[^/]+)/users/add/(?P<username>[^/]+)/$' % url_key, group.group_user_add, name=prefix+'group-user-add'),
        url(r'^%s/(?P<group>[^/]+)/users/delete/(?P<username>[^/]+)/$' % url_key, group.group_user_delete, name=prefix+'group-user-delete'),
        url(r'^%s/(?P<group>[^/]+)/users/edit/(?P<username>[^/]+)/$' % url_key, group.group_user_update, name=prefix+'group-user-edit'),
        url(r'^%s/(?P<group>[^/]+)/users/member-invite-select2/$' % url_key, group.user_group_member_invite_select2, name=prefix+'group-member-invite-select2'),
        url(r'^%s/(?P<group>[^/]+)/group-invite-select2/$' % url_key, group.group_invite_select2, name=prefix+'group-invite-select2'),
        url(r'^%s/(?P<group>[^/]+)/group-group-invite-delete/$' % url_key, group.group_group_invite_delete, name=prefix+'group-group-invite-delete'),
        url(r'^%s/(?P<group>[^/]+)/export/$' % url_key, group.group_export, name=prefix+'group-export'),
    
        url(r'^%s/(?P<group>[^/]+)/widgets/add/$' % url_key, widget.widget_add_group, name=prefix+'widget-add-group-empty'),
        url(r'^%s/(?P<group>[^/]+)/widgets/add/(?P<app_name>[^/]+)/(?P<widget_name>[^/]+)/$' % url_key, widget.widget_add_group, name=prefix+'widget-add-group'),
        
        url(r'^%s/(?P<group>[^/]+)/reflectedassign/$' % url_key, group.group_assign_reflected_object, name=prefix+'group-assign-reflected'),
        url(r'^%s/(?P<group>[^/]+)/attachmentselect/(?P<model>[^/]+)$' % url_key, attached_object.attachable_object_select2_view, name=prefix+'attached_object_select2_view'),
    ]

urlpatterns += url_registry.urlpatterns

# URLs for API version 2
router = routers.SimpleRouter()
router.register(r'public_conferences', PublicConferenceViewSet, basename='public_conference')
router.register(r'conferences', ConferenceViewSet, basename='conference')
router.register(r'groups', CosinnusSocietyViewSet, basename='group')
router.register(r'projects', CosinnusProjectViewSet, basename='project')
router.register(r'organizations', OrganizationViewSet, basename='organization')

# imports from external projects at this time may fail in certain test environments
try:
    from cosinnus_event.api.views import EventViewSet
    router.register(r'events', EventViewSet, basename='event')
except:
    pass
# imports from external projects at this time may fail in certain test environments
try:
    from cosinnus_note.api.views import NoteViewSet
    router.register(r'notes', NoteViewSet, basename='note')
except:
    pass
    
if getattr(settings, 'COSINNUS_API_SETTINGS', {}).get('user'):
    router.register(r'users', UserViewSet, basename='user')

if settings.COSINNUS_ROCKET_EXPORT_ENABLED:
    # imports from external projects at this time may fail in certain test environments
    try:
        from cosinnus_message.api.views import MessageExportView
        urlpatterns += [
            url(r'api/v2/rocket-export/', MessageExportView.as_view()),
        ]
    except:
        pass
    
if getattr(settings, 'COSINNUS_EMPTY_FILE_DOWNLOAD_NAME', None):
    urlpatterns += [
        url(f'{settings.COSINNUS_EMPTY_FILE_DOWNLOAD_NAME}', common.empty_file_download),
    ]

urlpatterns += [
    url(r'^o/me/', oauth_current_user),
    url(r'^o/user/', oauth_user),
    url(r'^o/profile/', oauth_profile),
]

schema_url_patterns = [
    url(r'^api/v2/token/', obtain_jwt_token),
    url(r'^api/v2/token/refresh/', refresh_jwt_token),
    url(r'^api/v2/current_user/', current_user, name='api-current-user'),
    url(r'^api/v2/settings/$', api_settings, name='api-settings'),
    url(r'^api/v2/statistics/', api_statistics, name='api-statistics'),
    url(r'^api/v2/jsi18n/$', translations, name='api-jsi18n'),
    url(r'^api/v2/', include((router.urls, 'api'), namespace='api')),
]

urlpatterns += schema_url_patterns

schema_view = get_schema_view(
    openapi.Info(
        title="WECHANGE API",
        default_version='v2',
        description="WECHANGE API (in progress)",
        terms_of_service="https://wechange.de/cms/nutzungsbedingungen/",
        contact=openapi.Contact(email="support@wechange.de"),
        license=openapi.License(name="AGPL 3.0"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    patterns=schema_url_patterns,
)

urlpatterns += [
    url(r'^api/v2/(?:header|navbar)/$', header, name='api-header'),
    url(r'^api/v2/footer/$', footer, name='api-footer'),
    url(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    url(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    url(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    url(r'^api/v2/docs/$', RedirectView.as_view(url='/swagger/', permanent=False)),
]
