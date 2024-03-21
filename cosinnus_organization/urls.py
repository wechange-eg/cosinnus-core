from django.conf import settings
from django.urls import path

from cosinnus.views import map
from cosinnus_organization.views import organization, membership, group

app_name = 'organization'

cosinnus_group_patterns = [
]

cosinnus_root_patterns = [
    path('organizations/', map.tile_view, name='organization-list', kwargs={'types': ['organizations']}),
    path('organizations/mine/', map.tile_view, name='organization-list-mine', kwargs={'types': ['organizations'], 'show_mine': True}),
    path('organizations/add/', organization.organization_create, name='organization-create'),
    path('organizations/<str:organization>/', organization.organization_detail, name='organization-detail'),
    path('organizations/<str:organization>/edit/', organization.organization_edit, name='organization-edit'),
    path('organizations/<str:organization>/delete/', organization.organization_delete, name='organization-delete'),

    path('organizations/<str:organization>/members/', membership.organization_members, name='organization-members'),
    path('organizations/<str:organization>/members/join/', membership.organization_user_join, name='organization-user-join'),
    path('organizations/<str:organization>/members/auto-join/', membership.organization_user_join_csrf_exempt, name='organization-user-join-nocsrf'),
    path('organizations/<str:organization>/members/leave/', membership.organization_user_leave, name='organization-user-leave'),
    path('organizations/<str:organization>/members/withdraw/', membership.organization_user_withdraw, name='organization-user-withdraw'),
    path('organizations/<str:organization>/members/decline/', membership.organization_user_invitation_decline, name='organization-user-decline'),
    path('organizations/<str:organization>/members/accept/', membership.organization_user_invitation_accept, name='organization-user-accept'),
    path('organizations/<str:organization>/members/add/', membership.organization_user_add, name='organization-user-add-generic'),
    path('organizations/<str:organization>/members/add-multiple/', membership.organization_user_add_multiple, name='organization-user-add-multiple'),
    path('organizations/<str:organization>/members/add/<str:username>/', membership.organization_user_add, name='organization-user-add'),
    path('organizations/<str:organization>/members/delete/<str:username>/', membership.organization_user_delete, name='organization-user-delete'),
    path('organizations/<str:organization>/members/edit/<str:username>/', membership.organization_user_update, name='organization-user-edit'),
    path('organizations/<str:organization>/members/member-invite-select2/', membership.user_organization_member_invite_select2, name='organization-member-invite-select2'),

    path('organizations/<str:organization>/groups/', group.organization_groups, name='organization-groups'),
    path('organizations/<str:organization>/groups/invite/', group.organization_group_invite, name='organization-group-invite'),
    path('organizations/<str:organization>/groups/group-invite-select2/', group.organization_group_invite_select2, name='organization-group-invite-select2'),
    path('organizations/<str:organization>/groups/<str:group>/accept/', group.organization_group_accept, name='organization-group-accept'),
    path('organizations/<str:organization>/groups/<str:group>/decline/', group.organization_group_decline, name='organization-group-decline'),
    path('organizations/<str:organization>/groups/<str:group>/withdraw/', group.organization_group_withdraw, name='organization-group-withdraw'),
    path('organizations/<str:organization>/groups/<str:group>/delete/', group.organization_group_delete, name='organization-group-delete'),
]

urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns