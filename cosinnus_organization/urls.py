from django.conf import settings
from django.conf.urls import url

from cosinnus.views import map
from cosinnus_organization.views import organization, membership, group

app_name = 'organization'

cosinnus_group_patterns = [
]

cosinnus_root_patterns = [
    url(r'^organizations/$', map.tile_view, name='organization-list', kwargs={'types': ['organizations']}),
    url(r'^organizations/mine/$', map.tile_view, name='organization-list-mine', kwargs={'types': ['organizations'], 'show_mine': True}),
    url(r'^organizations/add/$', organization.organization_create, name='organization-create'),
    url(r'^organizations/(?P<organization>[^/]+)/$', organization.organization_detail, name='organization-detail'),
    url(r'^organizations/(?P<organization>[^/]+)/edit/$', organization.organization_edit, name='organization-edit'),
    url(r'^organizations/(?P<organization>[^/]+)/delete/$', organization.organization_delete, name='organization-delete'),

    url(r'^organizations/(?P<organization>[^/]+)/members/$', membership.organization_members, name='organization-members'),
    url(r'^organizations/(?P<organization>[^/]+)/members/join/$', membership.organization_user_join, name='organization-user-join'),
    url(r'^organizations/(?P<organization>[^/]+)/members/auto-join/$', membership.organization_user_join_csrf_exempt, name='organization-user-join-nocsrf'),
    url(r'^organizations/(?P<organization>[^/]+)/members/leave/$', membership.organization_user_leave, name='organization-user-leave'),
    url(r'^organizations/(?P<organization>[^/]+)/members/withdraw/$', membership.organization_user_withdraw, name='organization-user-withdraw'),
    url(r'^organizations/(?P<organization>[^/]+)/members/decline/$', membership.organization_user_invitation_decline, name='organization-user-decline'),
    url(r'^organizations/(?P<organization>[^/]+)/members/accept/$', membership.organization_user_invitation_accept, name='organization-user-accept'),
    url(r'^organizations/(?P<organization>[^/]+)/members/add/$', membership.organization_user_add, name='organization-user-add-generic'),
    url(r'^organizations/(?P<organization>[^/]+)/members/add-multiple/$', membership.organization_user_add_multiple, name='organization-user-add-multiple'),
    url(r'^organizations/(?P<organization>[^/]+)/members/add/(?P<username>[^/]+)/$', membership.organization_user_add, name='organization-user-add'),
    url(r'^organizations/(?P<organization>[^/]+)/members/delete/(?P<username>[^/]+)/$', membership.organization_user_delete, name='organization-user-delete'),
    url(r'^organizations/(?P<organization>[^/]+)/members/edit/(?P<username>[^/]+)/$', membership.organization_user_update, name='organization-user-edit'),
    url(r'^organizations/(?P<organization>[^/]+)/members/member-invite-select2/$', membership.user_organization_member_invite_select2, name='organization-member-invite-select2'),

    url(r'^organizations/(?P<organization>[^/]+)/groups/$', group.organization_groups, name='organization-groups'),
    url(r'^organizations/(?P<organization>[^/]+)/groups/invite/$', group.organization_group_invite, name='organization-group-invite'),
    url(r'^organizations/(?P<organization>[^/]+)/groups/group-invite-select2/$', group.organization_group_invite_select2, name='organization-group-invite-select2'),
    url(r'^organizations/(?P<organization>[^/]+)/groups/(?P<group>[^/]+)/accept/$', group.organization_group_accept, name='organization-group-accept'),
    url(r'^organizations/(?P<organization>[^/]+)/groups/(?P<group>[^/]+)/decline/$', group.organization_group_decline, name='organization-group-decline'),
    url(r'^organizations/(?P<organization>[^/]+)/groups/(?P<group>[^/]+)/withdraw/$', group.organization_group_withdraw, name='organization-group-withdraw'),
    url(r'^organizations/(?P<organization>[^/]+)/groups/(?P<group>[^/]+)/delete/$', group.organization_group_delete, name='organization-group-delete'),
]

urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns