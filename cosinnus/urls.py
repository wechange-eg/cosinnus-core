# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import include, url
from django.urls import reverse_lazy
from django.views.generic.base import RedirectView, TemplateView
from rest_framework import routers
from rest_framework_swagger.views import get_swagger_view

from cosinnus.core.registries import url_registry
from cosinnus.conf import settings
from cosinnus.core.registries.group_models import group_model_registry
from cosinnus.templatetags.cosinnus_tags import is_integrated_portal, is_sso_portal
from cosinnus.api.views import CosinnusSocietyViewSet, CosinnusProjectViewSet, \
    OrganisationViewSet, UserView
from cosinnus.views import map, map_api, user, profile, common, widget, search, feedback, group,\
    statistics, housekeeping, facebook_integration, microsite, idea, attached_object, authentication,\
    user_dashboard, ui_prefs, administration
from cosinnus_event.api.views import EventViewSet
from django_otp.views import LoginView

schema_view = get_swagger_view(title='WECHANGE API')

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
    url(r'^projects/mine/$', map.tile_view, name='group-list-mine', kwargs={'types': ['projects'], 'show_mine': True}),
    url(r'^groups/mine/$', map.tile_view, name='group__group-list-mine', kwargs={'types': ['groups'], 'show_mine': True}),
    
    url(r'^map/embed/$', map.map_embed_view, name='map-embed'),
    url(r'^map/search/$', map_api.map_search_endpoint, name='map-search-endpoint'),
    url(r'^map/search/(?P<filter_group_id>\d+)/$', map_api.map_search_endpoint, name='map-search-endpoint-filtered'),
    url(r'^map/detail/$', map_api.map_detail_endpoint, name='map-detail-endpoint'),
    
    url(r'^likefollow/$', common.do_likefollow,  name='likefollow-view'),
    
    
    url(r'^invitations/$', group.group_list_invited, name='invitations', kwargs={'show_all': True}),
    url(r'^welcome/$', user.welcome_settings, name='welcome-settings'),
    url(r'^join/$', user.group_invite_token_enter_view, name='group-invite-token-enter'),
    url(r'^join/(?P<token>[^/]+)/$', user.group_invite_token_view, name='group-invite-token'),
    
    url(r'^account/report/$', feedback.report_object, name='report-object'),
    url(r'^account/accept_updated_tos/$', user.accept_updated_tos, name='accept-updated-tos'),
    
    url(r'^administration/approve_user/(?P<user_id>\d+)/$', user.approve_user, name='user-approve'),
    url(r'^administration/deny_user/(?P<user_id>\d+)/$', user.deny_user, name='user-deny'),
    url(r'^administration/verify_email/(?P<email_verification_param>[^/]+)/$', user.verifiy_user_email, name='user-verifiy-email'),
    url(r'^administration/list-unsubscribe/(?P<email>[^/]+)/(?P<token>[^/]+)/$', user.add_email_to_blacklist, name='user-add-email-blacklist'),
    url(r'^administration/deactivated/$', group.group_list_mine_deactivated, name='deactivated-groups'),
    url(r'^administration/activate/(?P<group_id>\d+)/$', group.activate_or_deactivate, name='group-activate', kwargs={'activate': True}),
    url(r'^administration/deactivate/(?P<group_id>\d+)/$', group.activate_or_deactivate, name='group-deactivate', kwargs={'activate': False}),
    url(r'^administration/login-2fa/$', authentication.admin_only_otp_token_validation, name='login-2fa'),
    
    # these URLs belong to the frontend administration area for superusers
    url(r'^administration/$', administration.administration, name='administration'),
    url(r'^administration/welcome_email/$', administration.welcome_email_edit, name='administration-welcome-email'),
    
    url(r'^statistics/simple/$', statistics.simple_statistics, name='simple-statistics'),
    
    #url(r'^housekeeping/$', housekeeping.housekeeping, name='housekeeping'),
    url(r'^housekeeping/deletespamusers/$', housekeeping.delete_spam_users, name='housekeeping_delete_spam_users'),
    url(r'^housekeeping/movegroupcontent/(?P<fromgroup>[^/]+)/(?P<togroup>[^/]+)/$', housekeeping.move_group_content, name='housekeeping_move_group_content'),
    url(r'^housekeeping/recreategroupwidgets/$', housekeeping.recreate_all_group_widgets, name='housekeeping_recreate_all_group_widgets'),
    url(r'^housekeeping/setcache/(?P<content>[^/]+)/$', housekeeping.setcache, name='housekeeping-setcache'),
    url(r'^housekeeping/fillcache/(?P<number>[^/]+)/$', housekeeping.fillcache, name='housekeeping-fillcache'),
    url(r'^housekeeping/getcache$', housekeeping.getcache, name='housekeeping-getcache'),
    url(r'^housekeeping/deletecache$', housekeeping.deletecache, name='housekeeping-deletecache'),
    url(r'^housekeeping/validate_redirects', housekeeping.check_and_delete_loop_redirects, name='housekeeping-validate-redirects'),
    url(r'^housekeeping/add_members_to_forum', housekeeping.add_members_to_forum, name='housekeeping-add-members-to-forum'),
    url(r'^housekeeping/user_statistics', housekeeping.user_statistics, name='housekeeping-user-statistics'),
    url(r'^housekeeping/create_map_test_entities/(?P<count>\d+)/', housekeeping.create_map_test_entities, name='housekeeping-create-map-test-entities'),
    url(r'^housekeeping/reset_user_tos_flags/', housekeeping.reset_user_tos_flags, name='housekeeping-reset-user-tos-flags'),
    url(r'^housekeeping/send_testmail/', housekeeping.send_testmail, name='housekeeping-send-testmail'),
    url(r'^housekeeping/print_settings/', housekeeping.print_settings, name='housekeeping-print-settings'),
    url(r'^housekeeping/group_storage_info/', housekeeping.group_storage_info, name='housekeeping-group-storage-info'),
    url(r'^housekeeping/group_storage_report/', housekeeping.group_storage_report_csv, name='housekeeping-group-storage-report'),
    url(r'^housekeeping/project_storage_report/', housekeeping.project_storage_report_csv, name='housekeeping-project-storage-report'),
    url(r'^housekeeping/user_activity_info/', housekeeping.user_activity_info, name='housekeeping-user-activity-info'),
    
    url(r'^select2/', include(('cosinnus.urls_select2', 'select2'), namespace='select2')),
]

if getattr(settings, 'COSINNUS_USE_V2_DASHBOARD', False) or getattr(settings, 'COSINNUS_USE_V2_DASHBOARD_ADMIN_ONLY', False):
    urlpatterns += [
        url(r'^dashboard/$', user_dashboard.user_dashboard_view, name='user-dashboard'),
        url(r'^dashboard/api/user_groups/$', user_dashboard.api_user_groups, name='user-dashboard-api-groups'),
        url(r'^dashboard/api/user_liked_ideas/$', user_dashboard.api_user_liked_ideas, name='user-dashboard-api-liked-ideas'),
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
        
        url(r'^%s/(?P<group>[^/]+)/users/$' % url_key, group.group_user_list, name=prefix+'group-user-list'),
        url(r'^%s/(?P<group>[^/]+)/users/add/$' % url_key, group.group_user_add, name=prefix+'group-user-add-generic'),
        url(r'^%s/(?P<group>[^/]+)/users/add/(?P<username>[^/]+)/$' % url_key, group.group_user_add, name=prefix+'group-user-add'),
        url(r'^%s/(?P<group>[^/]+)/users/delete/(?P<username>[^/]+)/$' % url_key, group.group_user_delete, name=prefix+'group-user-delete'),
        url(r'^%s/(?P<group>[^/]+)/users/edit/(?P<username>[^/]+)/$' % url_key, group.group_user_update, name=prefix+'group-user-edit'),
        url(r'^%s/(?P<group>[^/]+)/export/$' % url_key, group.group_export, name=prefix+'group-export'),
    
        url(r'^%s/(?P<group>[^/]+)/widgets/add/$' % url_key, widget.widget_add_group, name=prefix+'widget-add-group-empty'),
        url(r'^%s/(?P<group>[^/]+)/widgets/add/(?P<app_name>[^/]+)/(?P<widget_name>[^/]+)/$' % url_key, widget.widget_add_group, name=prefix+'widget-add-group'),
        
        url(r'^%s/(?P<group>[^/]+)/reflectedassign/$' % url_key, group.group_assign_reflected_object, name=prefix+'group-assign-reflected'),
        url(r'^%s/(?P<group>[^/]+)/attachmentselect/(?P<model>[^/]+)$' % url_key, attached_object.attachable_object_select2_view, name=prefix+'attached_object_select2_view'),
    ]

urlpatterns += url_registry.urlpatterns

# URLs for API version 2
router = routers.SimpleRouter()
router.register(r'groups', CosinnusSocietyViewSet)
router.register(r'projects', CosinnusProjectViewSet)
router.register(r'organisation', OrganisationViewSet)
router.register(r'event', EventViewSet)

urlpatterns += [
    url(r'^o/me/', UserView.as_view()),
    url(r'^o/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    url(r'api/v2/docs/', get_swagger_view()),
    url(r'api/v2/', include(router.urls)),
]
