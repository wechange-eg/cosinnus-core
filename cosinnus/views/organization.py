from __future__ import unicode_literals

import logging
from builtins import object

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DeleteView
from extra_views import CreateWithInlinesView, UpdateWithInlinesView

from ajax_forms.ajax_forms import AjaxFormsDeleteViewMixin
from cosinnus.api.serializers.group import OrganizationSimpleSerializer
from cosinnus.conf import settings
from cosinnus.forms.organization import CosinnusOrganizationForm, CosinnusOrganizationLocationInlineFormset, \
    CosinnusOrganizationSocialMediaInlineFormset
from cosinnus.models.organization import CosinnusOrganization, CosinnusOrganizationMembership, \
    CosinnusUnregisteredUserOrganizationInvite
from cosinnus.utils.permissions import check_user_superuser
from cosinnus.views.group import SamePortalGroupMixin, GroupDetailView, GroupUserListView, GroupConfirmMixin, \
    GroupUserJoinView, CSRFExemptGroupJoinView, GroupUserLeaveView, GroupUserWithdrawView, \
    GroupUserInvitationDeclineView, GroupUserInvitationAcceptView, GroupUserInviteView, GroupUserInviteMultipleView, \
    GroupUserUpdateView, GroupUserDeleteView, UserGroupMemberInviteSelect2View
from cosinnus.views.mixins.avatar import AvatarFormMixin
from cosinnus.views.mixins.group import RequireLoggedInMixin, RequireWriteGrouplessMixin

logger = logging.getLogger('cosinnus')


class CosinnusOrganizationFormMixin(object):
    form_class = CosinnusOrganizationForm
    model = CosinnusOrganization
    template_name = 'cosinnus/organization/organization_form.html'

    inlines = [CosinnusOrganizationLocationInlineFormset, CosinnusOrganizationSocialMediaInlineFormset]

    def get_form_kwargs(self):
        kwargs = super(CosinnusOrganizationFormMixin, self).get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, *args, **kwargs):
        ret = super(CosinnusOrganizationFormMixin, self).form_valid(*args, **kwargs)
        self.object.update_index()
        return ret

    def dispatch(self, *args, **kwargs):
        """ Find out which type of CosinnusOrganization (project/society), we're dealing with here. """
        # special check, if group/project creation is limited to admins, deny regular users creating groups/projects
        if getattr(settings, 'COSINNUS_LIMIT_PROJECT_AND_GROUP_CREATION_TO_ADMINS', False) \
                and not check_user_superuser(self.request.user) and self.form_view == 'add':
            messages.warning(self.request, _('Sorry, only portal administrators can create projects and groups!'))
            return redirect(reverse('cosinnus:portal-admin-list'))

        # special check: only portal admins can create groups
        if not getattr(settings, 'COSINNUS_USERS_CAN_CREATE_GROUPS', False) \
                and self.form_view == 'add':
            if not check_user_superuser(self.request.user):

                if getattr(settings, 'COSINNUS_CUSTOM_PREMIUM_PAGE_ENABLED', False):
                    redirect_url = reverse('cosinnus:premium-info-page')
                else:
                    messages.warning(self.request, _(
                        'Sorry, only portal administrators can create Organizations! You can either create a Project, or write a message to one of the administrators to create a Organization for you. Below you can find a listing of all administrators.'))
                    redirect_url = reverse('cosinnus:portal-admin-list')
                return redirect(redirect_url)

        return super(CosinnusOrganizationFormMixin, self).dispatch(*args, **kwargs)


class OrganizationCreateView(RequireLoggedInMixin, AvatarFormMixin, CosinnusOrganizationFormMixin,
                             CreateWithInlinesView):
    """ Create View for Organizations """

    form_view = 'add'
    slug_url_kwarg = 'organization'

    def get_context_data(self, **kwargs):
        context = super(OrganizationCreateView, self).get_context_data(**kwargs)
        context.update({
            'form_view': self.form_view,
        })
        return context

    def get_success_url(self):
        # Forward to next additional form
        if len(self.extra_forms) > 0:
            tab = self.request.GET.get('tab', 0)
            if tab < len(self.extra_forms):
                return reverse('cosinnus:organization-edit', kwargs={'organization': self.object.slug}) + f"./?tab={tab + 1}"
        return self.object.get_absolute_url() + '&action=create'


class OrganizationEditView(RequireWriteGrouplessMixin, AvatarFormMixin, CosinnusOrganizationFormMixin,
                           UpdateWithInlinesView):
    form_view = 'edit'
    slug_url_kwarg = 'organization'

    def get_context_data(self, **kwargs):
        context = super(OrganizationEditView, self).get_context_data(**kwargs)
        context.update({
            'form_view': self.form_view,
        })
        return context

    def get_success_url(self):
        return self.object.get_absolute_url() + '&action=edit'


class OrganizationDeleteView(RequireWriteGrouplessMixin, SamePortalGroupMixin, AjaxFormsDeleteViewMixin,
                             DeleteView):
    model = CosinnusOrganization
    slug_url_kwarg = 'organization'
    message_success = _('Your organization was deleted successfully.')

    def get_success_url(self):
        # disabled the success message for now as it isn't displayed on the map
        # messages.success(self.request, self.message_success)
        return reverse('cosinnus:organization-list-mine')


class OrganizationMembersView(GroupDetailView):
    template_name = 'cosinnus/organization/organization_detail.html'
    serializer_class = OrganizationSimpleSerializer
    membership_class = CosinnusOrganizationMembership
    invite_class = CosinnusUnregisteredUserOrganizationInvite
    group_url_kwarg = 'organization'


class OrganizationUserListView(GroupUserListView):
    serializer_class = OrganizationSimpleSerializer
    template_name = 'cosinnus/organization/organization_user_list.html'
    group_url_kwarg = 'organization'


class OrganizationConfirmMixin(GroupConfirmMixin):
    model = CosinnusOrganization
    success_url = reverse_lazy('cosinnus:organization-list')
    group_url_kwarg = 'organization'


class OrganizationUserJoinView(GroupUserJoinView):
    membership_class = CosinnusOrganizationMembership
    model = CosinnusOrganization
    success_url = reverse_lazy('cosinnus:group-list')
    group_url_kwarg = 'organization'


class CSRFExemptOrganizationJoinView(CSRFExemptGroupJoinView):
    membership_class = CosinnusOrganizationMembership
    model = CosinnusOrganization
    success_url = reverse_lazy('cosinnus:group-list')
    group_url_kwarg = 'organization'


class OrganizationUserLeaveView(GroupUserLeaveView):
    membership_class = CosinnusOrganizationMembership
    model = CosinnusOrganization
    success_url = reverse_lazy('cosinnus:group-list')
    group_url_kwarg = 'organization'


class OrganizationUserWithdrawView(GroupUserWithdrawView):
    membership_class = CosinnusOrganizationMembership
    model = CosinnusOrganization
    success_url = reverse_lazy('cosinnus:group-list')
    group_url_kwarg = 'organization'


class OrganizationUserInvitationDeclineView(GroupUserInvitationDeclineView):
    model = CosinnusOrganization
    membership_class = CosinnusOrganizationMembership
    group_url_kwarg = 'organization'


class OrganizationUserInvitationAcceptView(GroupUserInvitationAcceptView):
    model = CosinnusOrganization
    slug_url_kwarg = 'organization'
    membership_class = CosinnusOrganizationMembership
    group_url_kwarg = 'organization'


class OrganizationUserInviteView(GroupUserInviteView):
    model = CosinnusOrganizationMembership
    template_name = 'cosinnus/organization/organization_detail.html'
    membership_class = CosinnusOrganizationMembership
    group_url_kwarg = 'organization'

    def get_success_url(self):
        return reverse('cosinnus:organization-members', kwargs={'organization': self.group.slug})


class OrganizationUserInviteMultipleView(GroupUserInviteMultipleView):
    model = CosinnusOrganizationMembership
    template_name = 'cosinnus/organization/organization_detail.html'
    membership_class = CosinnusOrganizationMembership
    group_url_kwarg = 'organization'


class OrganizationUserUpdateView(GroupUserUpdateView):
    model = CosinnusOrganizationMembership
    membership_class = CosinnusOrganizationMembership
    group_url_kwarg = 'organization'

    def get_success_url(self):
        return reverse('cosinnus:organization-members', kwargs={'organization': self.group.slug})


class OrganizationUserDeleteView(GroupUserDeleteView):
    model = CosinnusOrganizationMembership
    membership_class = CosinnusOrganizationMembership
    group_url_kwarg = 'organization'

    def get_success_url(self):
        return reverse('cosinnus:organization-members', kwargs={'organization': self.group.slug})


class UserOrganizationMemberInviteSelect2View(UserGroupMemberInviteSelect2View):
    group_url_kwarg = 'organization'


organization_create = OrganizationCreateView.as_view()
organization_edit = OrganizationEditView.as_view()
organization_delete = OrganizationDeleteView.as_view()
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
