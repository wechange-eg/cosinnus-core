from __future__ import unicode_literals

import logging

from django.urls import reverse, reverse_lazy

from cosinnus.models import MEMBERSHIP_ADMIN
from cosinnus.views.group import (
    CSRFExemptGroupJoinView,
    GroupConfirmMixin,
    GroupDetailView,
    GroupUserDeleteView,
    GroupUserInvitationAcceptView,
    GroupUserInvitationDeclineView,
    GroupUserInviteMultipleView,
    GroupUserInviteView,
    GroupUserJoinView,
    GroupUserLeaveView,
    GroupUserListView,
    GroupUserUpdateView,
    GroupUserWithdrawView,
    UserGroupMemberInviteSelect2View,
)
from cosinnus.views.select2 import GroupMembersView
from cosinnus_organization.api.serializers import OrganizationSimpleSerializer
from cosinnus_organization.models import (
    CosinnusOrganization,
    CosinnusOrganizationMembership,
    CosinnusUnregisteredUserOrganizationInvite,
)

logger = logging.getLogger('cosinnus')


class OrganizationMembersView(GroupDetailView):
    template_name = 'cosinnus/organization/organization_detail.html'
    serializer_class = OrganizationSimpleSerializer
    membership_class = CosinnusOrganizationMembership
    invite_class = CosinnusUnregisteredUserOrganizationInvite
    group_url_kwarg = 'organization'
    model = CosinnusOrganization


class OrganizationUserListView(GroupUserListView):
    serializer_class = OrganizationSimpleSerializer
    template_name = 'cosinnus/organization/organization_user_list.html'
    group_url_kwarg = 'organization'
    model = CosinnusOrganization


class OrganizationConfirmMixin(GroupConfirmMixin):
    model = CosinnusOrganization
    success_url = reverse_lazy('cosinnus:organization-list')
    group_url_kwarg = 'organization'

    def get(self, *args, **kwargs):
        # FIXME: Workaround to allow accepting invitations in map tile view
        return self.post(*args, **kwargs)

    def get_error_url(self, **kwargs):
        return self.request.META.get('HTTP_REFERER', reverse('cosinnus:map'))


class OrganizationUserJoinView(GroupUserJoinView, OrganizationConfirmMixin):
    membership_class = CosinnusOrganizationMembership
    model = CosinnusOrganization
    success_url = reverse_lazy('map')
    group_url_kwarg = 'organization'
    membership_status = MEMBERSHIP_ADMIN


class CSRFExemptOrganizationJoinView(CSRFExemptGroupJoinView, OrganizationConfirmMixin):
    membership_class = CosinnusOrganizationMembership
    model = CosinnusOrganization
    success_url = reverse_lazy('cosinnus:organization-list')
    group_url_kwarg = 'organization'
    membership_status = MEMBERSHIP_ADMIN


class OrganizationUserLeaveView(GroupUserLeaveView, OrganizationConfirmMixin):
    membership_class = CosinnusOrganizationMembership
    model = CosinnusOrganization
    success_url = reverse_lazy('cosinnus:organization-list')
    group_url_kwarg = 'organization'


class OrganizationUserWithdrawView(GroupUserWithdrawView, OrganizationConfirmMixin):
    membership_class = CosinnusOrganizationMembership
    model = CosinnusOrganization
    success_url = reverse_lazy('cosinnus:organization-list')
    group_url_kwarg = 'organization'


class OrganizationUserInvitationDeclineView(GroupUserInvitationDeclineView):
    model = CosinnusOrganization
    membership_class = CosinnusOrganizationMembership
    group_url_kwarg = 'organization'


class OrganizationUserInvitationAcceptView(GroupUserInvitationAcceptView, OrganizationConfirmMixin):
    model = CosinnusOrganization
    slug_url_kwarg = 'organization'
    membership_class = CosinnusOrganizationMembership
    group_url_kwarg = 'organization'
    membership_status = MEMBERSHIP_ADMIN


class OrganizationUserInviteView(GroupUserInviteView):
    model = CosinnusOrganizationMembership
    template_name = 'cosinnus/organization/organization_detail.html'
    membership_class = CosinnusOrganizationMembership
    group_url_kwarg = 'organization'
    membership_status = MEMBERSHIP_ADMIN

    def get_success_url(self):
        return reverse('cosinnus:organization-members', kwargs={'organization': self.group.slug})


class OrganizationUserInviteMultipleView(GroupUserInviteMultipleView):
    model = CosinnusOrganizationMembership
    template_name = 'cosinnus/organization/organization_detail.html'
    membership_class = CosinnusOrganizationMembership
    group_url_kwarg = 'organization'
    membership_status = MEMBERSHIP_ADMIN

    def get_success_url(self):
        return reverse('cosinnus:organization-members', kwargs={'organization': self.group.slug})


class OrganizationUserUpdateView(GroupUserUpdateView):
    model = CosinnusOrganizationMembership
    membership_class = CosinnusOrganizationMembership
    group_url_kwarg = 'organization'
    membership_status = MEMBERSHIP_ADMIN

    def get_success_url(self):
        return reverse('cosinnus:organization-members', kwargs={'organization': self.group.slug})


class OrganizationUserDeleteView(GroupUserDeleteView):
    model = CosinnusOrganizationMembership
    membership_class = CosinnusOrganizationMembership
    group_url_kwarg = 'organization'
    membership_status = MEMBERSHIP_ADMIN

    def get_success_url(self):
        return reverse('cosinnus:organization-members', kwargs={'organization': self.group.slug})


class UserOrganizationMemberInviteSelect2View(UserGroupMemberInviteSelect2View):
    group_url_kwarg = 'organization'


class OrganizationMembersSelect2View(GroupMembersView):
    group_slug_field = 'organization'
    group_class = CosinnusOrganization


organization_members = OrganizationMembersView.as_view()
organization_user_list = OrganizationUserListView.as_view()
organization_user_list_api = OrganizationUserListView.as_view(is_ajax_request_url=True)
organization_user_join = OrganizationUserJoinView.as_view()
organization_user_join_csrf_exempt = CSRFExemptOrganizationJoinView.as_view()
organization_user_leave = OrganizationUserLeaveView.as_view()
organization_user_withdraw = OrganizationUserWithdrawView.as_view()
organization_user_invitation_decline = OrganizationUserInvitationDeclineView.as_view()
organization_user_invitation_accept = OrganizationUserInvitationAcceptView.as_view()
organization_user_add = OrganizationUserInviteView.as_view()
organization_user_add_api = OrganizationUserInviteView.as_view(is_ajax_request_url=True)
organization_user_add_multiple = OrganizationUserInviteMultipleView.as_view()
organization_user_update = OrganizationUserUpdateView.as_view()
organization_user_update_api = OrganizationUserUpdateView.as_view(is_ajax_request_url=True)
organization_user_delete = OrganizationUserDeleteView.as_view()
organization_user_delete_api = OrganizationUserDeleteView.as_view(is_ajax_request_url=True)
user_organization_member_invite_select2 = UserOrganizationMemberInviteSelect2View.as_view()
organization_members_select2 = OrganizationMembersSelect2View.as_view()
