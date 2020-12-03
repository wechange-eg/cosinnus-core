from __future__ import unicode_literals

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.db.transaction import atomic
from django.http import HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView, FormView
from django_select2 import Select2View, NO_ERR_RESP
from django.utils.translation import ugettext_lazy as _

from cosinnus.core import signals
from cosinnus.forms.group import MultiGroupSelectForm
from cosinnus.models import CosinnusPortal, force_text, group_aware_reverse
from cosinnus.models.group_extra import ensure_group_type
from cosinnus.models.membership import MEMBERSHIP_ADMIN, MEMBERSHIP_MEMBER, MEMBERSHIP_PENDING, \
    MEMBERSHIP_INVITED_PENDING
from cosinnus.utils.group import get_group_query_filter_for_search_terms, get_cosinnus_group_model
from cosinnus.utils.permissions import check_object_read_access, check_user_superuser
from cosinnus.utils.user import get_group_select2_pills
from cosinnus.views.group import SamePortalGroupMixin
from cosinnus.views.mixins.group import RequireReadMixin, RequireAdminMixin
from cosinnus_organization.forms import CosinnusOrganizationGroupForm
from cosinnus_organization.models import CosinnusOrganization, CosinnusOrganizationGroup
from cosinnus_organization.utils import get_organization_select2_pills

logger = logging.getLogger('cosinnus')


class OrganizationGroupsView(DetailView):
    template_name = 'cosinnus/organization/groups.html'
    model = CosinnusOrganization
    slug_url_kwarg = 'organization'

    def get_context_data(self, **kwargs):
        context = super(OrganizationGroupsView, self).get_context_data(**kwargs)
        queryset = self.object.groups
        context.update({
            'invited': queryset.filter(status=MEMBERSHIP_INVITED_PENDING),
            'pendings': queryset.filter(status=MEMBERSHIP_PENDING),
            'members': queryset.filter(status__in=(MEMBERSHIP_MEMBER, MEMBERSHIP_ADMIN)),
            'invite_form': MultiGroupSelectForm(organization=self.object),
        })
        return context


class OrganizationGroupInviteView(RequireAdminMixin, FormView):
    form_class = MultiGroupSelectForm
    template_name = 'cosinnus/organization/groups.html'
    group_url_kwarg = 'organization'
    group_attr = 'organization'

    def get(self, *args, **kwargs):
        messages.error(self.request, _('This action is not available directly!'))
        return redirect(reverse('cosinnus:organization-detail', kwargs={'organization': kwargs.get('organization', '<NOORGKWARG>')}))

    def get_success_url(self):
        return reverse('cosinnus:organization-groups', kwargs={'organization': self.organization.slug})

    def get_form_kwargs(self):
        kwargs = super(OrganizationGroupInviteView, self).get_form_kwargs()
        kwargs['organization'] = self.organization
        return kwargs

    def form_valid(self, form):
        groups = form.cleaned_data.get('groups')
        for group in groups:
            self.invite(group, form)
        return HttpResponseRedirect(self.get_success_url())

    def invite(self, group, form):
        try:
            m = CosinnusOrganizationGroup.objects.get(group=group, organization=self.organization)
            # if the group has already requested a join when we try to invite him, accept him immediately
            if m.status == MEMBERSHIP_PENDING:
                m.status = MEMBERSHIP_MEMBER
                m.save()
                # update index for the group
                # typed_group = ensure_group_type(self.organization)
                # typed_group.update_index()
                signals.organization_group_request_accepted.send(sender=self, organization=self.organization, group=group)
                messages.success(self.request,_(
                    'Project/group %(name)s had already requested and has now been accepted.') % {
                                     'name': group.name})
                # trigger signal for accepting that user's join request
            return HttpResponseRedirect(self.get_success_url())
        except CosinnusOrganizationGroup.DoesNotExist:
            CosinnusOrganizationGroup.objects.create(organization=self.organization, group=group, status=MEMBERSHIP_INVITED_PENDING)
            signals.organization_group_invited.send(sender=self, organization=self.organization, group=group)

            messages.success(self.request,
                             _('Project/group %(name)s was successfully invited.') % {'name': group.name})
            return HttpResponseRedirect(self.get_success_url())


class OrganzationConfirmMixin(object):
    model = CosinnusOrganization
    slug_url_kwarg = 'organization'
    success_url = reverse_lazy('cosinnus:organization-list')

    def get(self, *args, **kwargs):
        """ We make the allowance to call this by GET if called with ?direct=1 param,
            so that user joins can be automated with a direct link (like after being recruited) """
        if not self.request.GET.get('direct', None) == '1':
            messages.error(self.request, _('This action is not available directly!'))
            return redirect(self.get_error_url(**kwargs))
        else:
            return self.post(*args, **kwargs)

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        self.confirm_action()
        # update index for the group
        # typed_group = ensure_group_type(self.object)
        # typed_group.update_index()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        """
        Returns the supplied success URL.
        """
        if self.success_url:
            # Forcing possible reverse_lazy evaluation
            url = force_text(self.success_url)
        else:
            raise ImproperlyConfigured(
                "No URL to redirect to. Provide a success_url.")
        return url

    def get_error_url(self, **kwargs):
        return group_aware_reverse('cosinnus:organization-groups', kwargs=kwargs)

    def confirm_action(self):
        raise NotImplementedError()


class OrganizationGroupWithdrawView(OrganzationConfirmMixin, DetailView):

    message_success = _('Your join request was withdrawn from organization “%(name)s” successfully.')

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(OrganizationGroupWithdrawView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.referer = request.META.get('HTTP_REFERER', reverse('cosinnus:organization-list'))
        return super(OrganizationGroupWithdrawView, self).post(request, *args, **kwargs)

    def get_success_url(self):
        # self.referer is set in post() method
        if not getattr(self, '_had_error', False):
            messages.success(self.request, self.message_success % {'name': self.object.name})
        return self.referer

    def confirm_action(self):
        try:
            membership = CosinnusOrganizationGroup.objects.get(
                organization=self.object,
                group__slug=self.kwargs.get('group'),
                status=MEMBERSHIP_PENDING
            )
            membership.delete()
        except CosinnusOrganizationGroup.DoesNotExist:
            self._had_error = True


class OrganizationGroupDeclineView(OrganizationGroupWithdrawView):

    message_success = _('You have declined the invitation to organization “%(name)s”.')

    def confirm_action(self):
        try:
            membership = CosinnusOrganizationGroup.objects.get(
                organization=self.object,
                group__slug=self.kwargs.get('group'),
                status=MEMBERSHIP_INVITED_PENDING
            )
            group = membership.group
            membership.delete()
            signals.organization_group_invitation_declined.send(sender=self, organization=self.object, group=group)
        except CosinnusOrganizationGroup.DoesNotExist:
            self._had_error = True


class OrganizationGroupAcceptView(OrganizationGroupWithdrawView):
    message_success = _('Your project/group is now assigned to the organization “%(name)s”. Welcome!')
    membership_status = MEMBERSHIP_MEMBER

    def confirm_action(self):
        try:
            membership = CosinnusOrganizationGroup.objects.get(
                organization=self.object,
                group__slug=self.kwargs.get('group'),
                status=MEMBERSHIP_INVITED_PENDING
            )
            membership.status = MEMBERSHIP_MEMBER
            membership.save()
            signals.organization_group_request_accepted.send(sender=self, organization=self.object, group=membership.group)
        except CosinnusOrganizationGroup.DoesNotExist:
            self._had_error = True


class GroupSelectMixin(object):
    form_class = CosinnusOrganizationGroupForm
    model = CosinnusOrganizationGroup
    slug_field = 'group__slug'
    slug_url_kwarg = 'group'

    @atomic
    def dispatch(self, request, *args, **kwargs):
        return super(GroupSelectMixin, self).dispatch(request, *args, **kwargs)

    def get(self, *args, **kwargs):
        messages.error(self.request, _('This action is not available directly!'))
        return redirect(
            reverse('cosinnus:organization-groups', kwargs={'organization': kwargs.get('organization', '<NOGROUPKWARG>')}))

    def get_form_kwargs(self):
        kwargs = super(GroupSelectMixin, self).get_form_kwargs()
        kwargs['organization'] = self.organization
        kwargs['group_qs'] = self.get_group_qs()
        return kwargs

    def get_initial(self):
        group = self.kwargs.get('group', None)
        if group:
            group = get_cosinnus_group_model()._default_manager.get(slug=group)
            return {'group': group}

    def get_queryset(self):
        return self.model.objects.filter(organization=self.organization)

    def get_success_url(self):
        referer = self.request.META.get('HTTP_REFERER', None)
        if referer:
            return referer
        return reverse('cosinnus:organization-groups', kwargs={'organization': self.organization.slug})


class OrganizationGroupDeleteView(RequireAdminMixin, GroupSelectMixin, DeleteView):
    group_url_kwarg = 'organization'
    group_attr = 'organization'
    membership_status = MEMBERSHIP_MEMBER

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        org = self.object.organization
        group = self.object.group
        status = self.object.status
        self.object.delete()

        if status == MEMBERSHIP_PENDING:
            signals.organization_group_invitation_declined.send(sender=self, organization=org, group=group)
            messages.success(self.request,
                             _('Your request was withdrawn from organization "%(name)s" successfully.') % {
                                 'name': org.name})
        if status == MEMBERSHIP_INVITED_PENDING:
            messages.success(self.request, _('Your invitation to project/group "%(name)s" was withdrawn successfully.') % {
                'name': group.name})
        if status == self.membership_status:
            messages.success(self.request,
                             _('Project/group "%(name)s" is no longer assigned.') % {'name': group.name})
        return HttpResponseRedirect(self.get_success_url())


class OrganizationGroupInviteSelect2View(RequireReadMixin, Select2View):
    """
    This view is used as API backend to serve the suggestions for the group field.
    """
    group_url_kwarg = 'organization'
    group_attr = 'organization'

    def check_all_permissions(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            raise PermissionDenied

    def get_results(self, request, term, page, context):
        terms = term.strip().lower().split(' ')
        q = get_group_query_filter_for_search_terms(terms)

        groups = get_cosinnus_group_model().objects.filter(q)
        groups = groups.filter(portal_id=CosinnusPortal.get_current().id, is_active=True)
        groups = groups.exclude(organizations__organization=self.organization)
        groups = [group for group in groups if check_object_read_access(group, request.user)]
        groups = sorted(groups, key=lambda org: org.name.lower())

        results = get_group_select2_pills(groups)

        # Any error response, Has more results, options list
        return (NO_ERR_RESP, False, results)


organization_groups = OrganizationGroupsView.as_view()
organization_group_invite = OrganizationGroupInviteView.as_view()
organization_group_accept = OrganizationGroupAcceptView.as_view()
organization_group_decline = OrganizationGroupDeclineView.as_view()
organization_group_withdraw = OrganizationGroupWithdrawView.as_view()
organization_group_delete = OrganizationGroupDeleteView.as_view()
organization_group_invite_select2 = OrganizationGroupInviteSelect2View.as_view()
