# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import include, patterns, url
from django.views.generic import TemplateView

from cosinnus.core.registries import url_registry
from cosinnus.conf import settings
from cosinnus.core.registries.group_models import group_model_registry
from cosinnus.templatetags.cosinnus_tags import is_integrated_portal,\
    is_sso_portal
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.generic.base import RedirectView
from django.core.urlresolvers import reverse_lazy

urlpatterns = patterns('cosinnus.views',
    # we do not define an index anymore and let CMS handle that.

    url(r'^users/$', 'user.user_list', name='user-list'),
    
    url(r'^map/$', 'maps.map_view', name='map'),
    url(r'^map/embed/$', 'maps.map_embed_view', name='map-embed'),
    
    url(r'^portal/admins/$', 'user.portal_admin_list', name='portal-admin-list'),
    #url(r'^users/map/$', 'user.user_list_map', name='user-list-map'),
    url(r'^user/(?P<username>[^/]+)/$', 'profile.detail_view', name='profile-detail'),
    #url(r'^user/(?P<username>[^/]+)/edit/$', 'user.user_update', name='user-edit'),
    
    url(r'^language/(?P<language>[^/]+)/$', 'common.switch_language', name='switch-language'),
    
    url(r'^widgets/list/$', 'widget.widget_list', name='widget-list'),
    url(r'^widgets/add/user/$', 'widget.widget_add_user', name='widget-add-user-empty'),
    url(r'^widgets/add/user/(?P<app_name>[^/]+)/(?P<widget_name>[^/]+)/$', 'widget.widget_add_user', name='widget-add-user'),
    url(r'^widgets/save/$', 'widget.save_widget_config', name='widget-save-config'),
    url(r'^widget/(?P<id>\d+)/$', 'widget.widget_detail', name='widget-detail'),
    url(r'^widget/(?P<id>\d+)/(?P<offset>\d+)/$', 'widget.widget_detail', name='widget-detail-offset'),
    url(r'^widget/(?P<id>\d+)/delete/$', 'widget.widget_delete', name='widget-delete'),
    url(r'^widget/(?P<id>\d+)/edit/$', 'widget.widget_edit', name='widget-edit'),
    url(r'^widget/(?P<id>\d+)/edit/(?P<app_name>[^/]+)/(?P<widget_name>[^/]+)/$', 'widget.widget_edit', name='widget-edit-swap'),

    url(r'^search/$', 'search.search', name='search'),
    
    url(r'^invitations/$', 'group.group_list_invited', name='invitations', kwargs={'show_all': True}),
    url(r'^welcome/$', 'user.welcome_settings', name='welcome-settings'),
    
    url(r'^account/report/$', 'feedback.report_object', name='report-object'),
    
    url(r'^administration/approve_user/(?P<user_id>\d+)/$', 'user.approve_user', name='user-approve'),
    url(r'^administration/deny_user/(?P<user_id>\d+)/$', 'user.deny_user', name='user-deny'),
    url(r'^administration/verify_email/(?P<email_verification_param>[^/]+)/$', 'user.verifiy_user_email', name='user-verifiy-email'),
    url(r'^administration/list-unsubscribe/(?P<email>[^/]+)/(?P<token>[^/]+)/$', 'user.add_email_to_blacklist', name='user-add-email-blacklist'),
    url(r'^administration/activate/(?P<group_id>\d+)/$', 'group.activate_or_deactivate', name='group-activate', kwargs={'activate': True}),
    url(r'^administration/deactivate/(?P<group_id>\d+)/$', 'group.activate_or_deactivate', name='group-deactivate', kwargs={'activate': False}),
    
    
    
    url(r'^housekeeping/$', 'housekeeping.housekeeping', name='housekeeping'),
    url(r'^housekeeping/deletespamusers/$', 'housekeeping.delete_spam_users', name='housekeeping_delete_spam_users'),
    url(r'^housekeeping/movegroupcontent/(?P<fromgroup>[^/]+)/(?P<togroup>[^/]+)/$', 'housekeeping.move_group_content', name='housekeeping_move_group_content'),
    url(r'^housekeeping/recreategroupwidgets/$', 'housekeeping.recreate_all_group_widgets', name='housekeeping_recreate_all_group_widgets'),
    url(r'^housekeeping/setcache/(?P<content>[^/]+)/$', 'housekeeping.setcache', name='housekeeping-setcache'),
    url(r'^housekeeping/fillcache/(?P<number>[^/]+)/$', 'housekeeping.fillcache', name='housekeeping-fillcache'),
    url(r'^housekeeping/getcache$', 'housekeeping.getcache', name='housekeeping-getcache'),
    url(r'^housekeeping/deletecache$', 'housekeeping.deletecache', name='housekeeping-deletecache'),
    url(r'^housekeeping/validate_redirects', 'housekeeping.check_and_delete_loop_redirects', name='housekeeping-validate-redirects'),
    url(r'^housekeeping/add_members_to_forum', 'housekeeping.add_members_to_forum', name='housekeeping-add-members-to-forum'),
    url(r'^housekeeping/user_statistics', 'housekeeping.user_statistics', name='housekeeping-user-statistics'),
    url(r'^housekeeping/create_map_test_entities/(?P<count>\d+)/', 'housekeeping.create_map_test_entities', name='housekeeping-create-map-test-entities'),
    url(r'^housekeeping/reset_user_tos_flags/', 'housekeeping.reset_user_tos_flags', name='housekeeping-reset-user-tos-flags'),
    url(r'^housekeeping/send_testmail/', 'housekeeping.send_testmail', name='housekeeping-send-testmail'),
    
    
    url(r'^select2/', include('cosinnus.urls_select2', namespace='select2')),
)

# shall we use the deprecated non-haystack Map query API?
if getattr(settings, 'COSINNUS_USE_DEPRECATED_NON_HAYSTACK_MAP_API', False):
    urlpatterns += patterns('cosinnus.views',
        url(r'^maps/search/$', 'maps.map_search_endpoint', name='map-search-endpoint'),
        url(r'^maps/search/(?P<filter_group_id>\d+)/$', 'maps.map_search_endpoint', name='map-search-endpoint-filtered'),
    )
else:
    urlpatterns += patterns('cosinnus.views',
        url(r'^maps/search/$', 'map_api.map_search_endpoint', name='map-search-endpoint'),
        url(r'^maps/search/(?P<filter_group_id>\d+)/$', 'map_api.map_search_endpoint', name='map-search-endpoint-filtered'),
    )

# some user management not allowed in integrated mode and sso-mode
if not is_integrated_portal() and not is_sso_portal():
    urlpatterns += patterns('cosinnus.views',
        url(r'^profile/dashboard/$', 'widget.user_dashboard', name='user-dashboard'),
        url(r'^profile/edit/$', 'profile.update_view', name='profile-edit'),
        url(r'^signup/$', 'user.user_create', name='user-add'),
    )

# some more user management not allowed in integrated mode
if not is_integrated_portal():
    urlpatterns += patterns('cosinnus.views',
        url(r'^profile/$', 'profile.detail_view', name='profile-detail'),
        url(r'^profile/delete/$', 'profile.delete_view', name='profile-delete'),
    )

# in SSO-portals we redirect the signup page to the login page
if is_sso_portal():
    urlpatterns += patterns('cosinnus.views',
        url(r'^signup/$', RedirectView.as_view(url=reverse_lazy('login'), permanent=False)),
    )
    
if settings.COSINNUS_FACEBOOK_INTEGRATION_ENABLED:
    urlpatterns += patterns('cosinnus.views', 
        url(r'^fb-integration/save-auth-tokens/$', 'facebook_integration.save_auth_tokens',  name='facebook-save-auth-tokens'),
        url(r'^fb-integration/remove-facebook/$', 'facebook_integration.remove_facebook_association',  name='facebook-remove-association'),
        url(r'^fb-integration/confirm-page-admin/(?P<group_id>\d+)/$', 'facebook_integration.confirm_page_admin',  name='facebook-confirm-page-admin'),
    )

for url_key in group_model_registry:
    plural_url_key = group_model_registry.get_plural_url_key(url_key, url_key + '_s')
    prefix = group_model_registry.get_url_name_prefix(url_key, '')
    
    urlpatterns += patterns('cosinnus.views',
        url(r'^%s/in-group-with/(?P<group>[^/]+)/$' % plural_url_key, 'group.group_list_filtered', name=prefix+'group-list-filtered'),
        url(r'^%s/mine/$' % plural_url_key, 'group.group_list_mine', name=prefix+'group-list-mine'),
        url(r'^%s/invited/$' % plural_url_key, 'group.group_list_invited', name=prefix+'group-list-invited'),
        url(r'^%s/$' % plural_url_key, 'group.group_list', name=prefix+'group-list'),
        #url(r'^%s/map/$' % plural_url_key, 'group.group_list_map', name=prefix+'group-list-map'),
        url(r'^%s/add/$' % plural_url_key, 'group.group_create', name=prefix+'group-add'),
        url(r'^%s/(?P<group>[^/]+)/$' % url_key, 'group.group_startpage', name=prefix+'group-dashboard'),
        url(r'^%s/(?P<group>[^/]+)/microsite/$' % url_key, 'microsite.group_microsite_view', name=prefix+'group-microsite'),
        #url(r'^%s/(?P<group>[^/]+)/_microsite__old_/$' % url_key, 'cms.group_microsite', name=prefix+'group-microsite'),
        #url(r'^%s/(?P<group>[^/]+)/_microsite__old_/edit/$' % url_key, 'cms.group_microsite_edit', name=prefix+'group-microsite-edit'),
        url(r'^%s/(?P<group>[^/]+)/members/$' % url_key, 'group.group_detail', name=prefix+'group-detail'),
        url(r'^%s/(?P<group>[^/]+)/members/recruit/$' % url_key, 'group.group_user_recruit', name=prefix+'group-user-recruit'),
        url(r'^%s/(?P<group>[^/]+)/members/recruitdelete/(?P<id>\d+)/$' % url_key, 'group.group_user_recruit_delete', name=prefix+'group-user-recruit-delete'),
        #url(r'^%s/(?P<group>[^/]+)/members/map/$' % url_key, 'group.group_members_map', name=prefix+'group-members-map'),
        url(r'^%s/(?P<group>[^/]+)/edit/$' % url_key, 'group.group_update', name=prefix+'group-edit'),
        url(r'^%s/(?P<group>[^/]+)/delete/$' % url_key, 'group.group_delete', name=prefix+'group-delete'),
        url(r'^%s/(?P<group>[^/]+)/join/$' % url_key, 'group.group_user_join', name=prefix+'group-user-join'),
        url(r'^%s/(?P<group>[^/]+)/leave/$' % url_key, 'group.group_user_leave', name=prefix+'group-user-leave'),
        url(r'^%s/(?P<group>[^/]+)/withdraw/$' % url_key, 'group.group_user_withdraw', name=prefix+'group-user-withdraw'),
        url(r'^%s/(?P<group>[^/]+)/decline/$' % url_key, 'group.group_user_invitation_decline', name=prefix+'group-user-decline'),
        url(r'^%s/(?P<group>[^/]+)/accept/$' % url_key, 'group.group_user_invitation_accept', name=prefix+'group-user-accept'),
        
        url(r'^%s/(?P<group>[^/]+)/users/$' % url_key, 'group.group_user_list', name=prefix+'group-user-list'),
        url(r'^%s/(?P<group>[^/]+)/users/add/$' % url_key, 'group.group_user_add', name=prefix+'group-user-add-generic'),
        url(r'^%s/(?P<group>[^/]+)/users/add/(?P<username>[^/]+)/$' % url_key, 'group.group_user_add', name=prefix+'group-user-add'),
        url(r'^%s/(?P<group>[^/]+)/users/delete/(?P<username>[^/]+)/$' % url_key, 'group.group_user_delete', name=prefix+'group-user-delete'),
        url(r'^%s/(?P<group>[^/]+)/users/edit/(?P<username>[^/]+)/$' % url_key, 'group.group_user_update', name=prefix+'group-user-edit'),
        url(r'^%s/(?P<group>[^/]+)/export/$' % url_key, 'group.group_export', name=prefix+'group-export'),
    
        url(r'^%s/(?P<group>[^/]+)/widgets/add/$' % url_key, 'widget.widget_add_group', name=prefix+'widget-add-group-empty'),
        url(r'^%s/(?P<group>[^/]+)/widgets/add/(?P<app_name>[^/]+)/(?P<widget_name>[^/]+)/$' % url_key, 'widget.widget_add_group', name=prefix+'widget-add-group'),
        
        url(r'^%s/(?P<group>[^/]+)/reflectedassign/$' % url_key, 'group.group_assign_reflected_object', name=prefix+'group-assign-reflected'),
        url(r'^%s/(?P<group>[^/]+)/attachmentselect/(?P<model>[^/]+)$' % url_key, 'attached_object.attachable_object_select2_view', name=prefix+'attached_object_select2_view'),
    )

urlpatterns += url_registry.urlpatterns
