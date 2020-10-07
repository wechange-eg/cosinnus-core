from django.conf import settings
from django.conf.urls import url

from cosinnus.views import map
from cosinnus_organization import views

app_name = 'organization'

cosinnus_group_patterns = [
]

cosinnus_root_patterns = [
    url(r'^organizations/$', map.tile_view, name='organization-list', kwargs={'types': ['organizations']}),
    url(r'^organizations/mine/$', map.tile_view, name='organization-list-mine', kwargs={'types': ['organizations'], 'show_mine': True}),
    url(r'^organizations/add/$', views.organization_create, name='organization-create'),
    url(r'^organizations/(?P<organization>[^/]+)/edit/$', views.organization_edit, name='organization-edit'),
    url(r'^organizations/(?P<organization>[^/]+)/delete/$', views.organization_delete, name='organization-delete'),
    url(r'^organizations/(?P<organization>[^/]+)/members/$', views.organization_members, name='organization-members'),
    url(r'^organizations/(?P<organization>[^/]+)/join/$', views.organization_user_join, name='organization-user-join'),
    url(r'^organizations/(?P<organization>[^/]+)/auto-join/$', views.organization_user_join_csrf_exempt, name='organization-user-join-nocsrf'),
    url(r'^organizations/(?P<organization>[^/]+)/leave/$', views.organization_user_leave, name='organization-user-leave'),
    url(r'^organizations/(?P<organization>[^/]+)/withdraw/$', views.organization_user_withdraw, name='organization-user-withdraw'),
    url(r'^organizations/(?P<organization>[^/]+)/decline/$', views.organization_user_invitation_decline, name='organization-user-decline'),
    url(r'^organizations/(?P<organization>[^/]+)/accept/$', views.organization_user_invitation_accept, name='organization-user-accept'),
    url(r'^organizations/(?P<organization>[^/]+)/users/$', views.organization_user_list, name='organization-user-list'),
    url(r'^organizations/(?P<organization>[^/]+)/users/add/$', views.organization_user_add, name='organization-user-add-generic'),
    url(r'^organizations/(?P<organization>[^/]+)/users/add-multiple/$', views.organization_user_add_multiple, name='organization-user-add-multiple'),
    url(r'^organizations/(?P<organization>[^/]+)/users/add/(?P<username>[^/]+)/$', views.organization_user_add, name='organization-user-add'),
    url(r'^organizations/(?P<organization>[^/]+)/users/delete/(?P<username>[^/]+)/$', views.organization_user_delete, name='organization-user-delete'),
    url(r'^organizations/(?P<organization>[^/]+)/users/edit/(?P<username>[^/]+)/$', views.organization_user_update, name='organization-user-edit'),
    url(r'^organizations/(?P<organization>[^/]+)/users/member-invite-select2/$', views.user_organization_member_invite_select2, name='organization-member-invite-select2'),
]

urlpatterns = cosinnus_group_patterns + cosinnus_root_patterns