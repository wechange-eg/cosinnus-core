# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse, reverse_lazy
from django.http import HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from django.views.generic import (CreateView, DeleteView, DetailView,
    ListView, UpdateView)

from cosinnus.core.decorators.views import superuser_required
from cosinnus.forms.group import CosinnusGroupForm, MembershipForm
from cosinnus.models import (CosinnusGroup, CosinnusGroupMembership,
    MEMBERSHIP_ADMIN, MEMBERSHIP_MEMBER, MEMBERSHIP_PENDING)
from cosinnus.views.mixins.group import RequireAdminMixin, RequireReadMixin


class GroupCreateView(CreateView):

    form_class = CosinnusGroupForm
    model = CosinnusGroup
    template_name = 'cosinnus/group_form.html'

    @method_decorator(superuser_required)
    def dispatch(self, *args, **kwargs):
        return super(GroupCreateView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(GroupCreateView, self).get_context_data(**kwargs)
        context['submit_label'] = _('Create')
        return context

    def get_success_url(self):
        return reverse('cosinnus:group-detail', kwargs={'group': self.object.slug})

group_create = GroupCreateView.as_view()


class GroupDeleteView(DeleteView):

    model = CosinnusGroup
    slug_url_kwarg = 'group'
    success_url = reverse_lazy('cosinnus:group-list')
    template_name = 'cosinnus/group_delete.html'

    @method_decorator(superuser_required)
    def dispatch(self, *args, **kwargs):
        return super(GroupDeleteView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(GroupDeleteView, self).get_context_data(**kwargs)
        context['submit_label'] = _('Delete')
        return context

group_delete = GroupDeleteView.as_view()


class GroupDetailView(RequireReadMixin, DetailView):

    template_name = 'cosinnus/group_detail.html'

    def get_object(self, queryset=None):
        return self.group

    def get_context_data(self, **kwargs):
        context = super(GroupDetailView, self).get_context_data(**kwargs)
        admin_ids = CosinnusGroupMembership.objects.get_admins(group=self.group)
        member_ids = CosinnusGroupMembership.objects.get_members(group=self.group)
        pending_ids = CosinnusGroupMembership.objects.get_pendings(group=self.group)
        _q = get_user_model()._default_manager.order_by('first_name', 'last_name') \
                             .select_related('cosinnus_profile')

        context.update({
            'admins': _q._clone().filter(id__in=admin_ids),
            'members': _q._clone().filter(id__in=member_ids),
            'pendings': _q._clone().filter(id__in=pending_ids),
        })
        return context

group_detail = GroupDetailView.as_view()


class GroupListView(ListView):

    model = CosinnusGroup
    template_name = 'cosinnus/group_list.html'

    def get_queryset(self):
        if self.request.user.is_authenticated():
            return self.model.objects.get_cached()
        else:
            return list(self.model.objects.public())

    def get_context_data(self, **kwargs):
        ctx = super(GroupListView, self).get_context_data(**kwargs)
        # TODO: get_many for membership and pending and adjust template
        _members = CosinnusGroupMembership.objects.get_members(groups=ctx['object_list'])
        _pendings = CosinnusGroupMembership.objects.get_pendings(groups=ctx['object_list'])
        members = (_members.get(g.pk, []) for g in ctx['object_list'])
        pendings = (_pendings.get(g.pk, []) for g in ctx['object_list'])
        ctx.update({
            'rows': zip(self.object_list, members, pendings),
        })
        return ctx

group_list = GroupListView.as_view()


class GroupUpdateView(RequireAdminMixin, UpdateView):

    form_class = CosinnusGroupForm
    model = CosinnusGroup
    template_name = 'cosinnus/group_form.html'

    def get_object(self, queryset=None):
        return self.group

    def get_context_data(self, **kwargs):
        context = super(GroupUpdateView, self).get_context_data(**kwargs)
        context['submit_label'] = _('Save')
        return context

    def get_success_url(self):
        return reverse('cosinnus:group-detail', kwargs={'group': self.group.slug})

group_update = GroupUpdateView.as_view()


class GroupUserListView(RequireReadMixin, ListView):

    template_name = 'cosinnus/group_user_list.html'

    def get_queryset(self):
        return self.group.users.all()

group_user_list = GroupUserListView.as_view()


class GroupConfirmMixin(object):

    model = CosinnusGroup
    slug_url_kwarg = 'group'
    success_url = reverse_lazy('cosinnus:group-list')

    def get_context_data(self, **kwargs):
        context = super(GroupConfirmMixin, self).get_context_data(**kwargs)
        context.update({
            'confirm_label': self.get_confirm_label(),
            'confirm_question': self.get_confirm_question(),
            'confirm_title': self.get_confirm_title(),
            'submit_css_classes': getattr(self, 'submit_css_classes', None)
        })
        return context

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        self.confirm_action()
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

    def confirm_action(self):
        raise NotImplementedError()

    def get_confirm_label(self):
        return self.confirm_label

    def get_confirm_question(self):
        return self.confirm_question % {'group_name': self.object.name}

    def get_confirm_title(self):
        return self.confirm_title % {'group_name': self.object.name}


class GroupUserJoinView(GroupConfirmMixin, DetailView):

    confirm_label = _('Join')
    confirm_question = _('Do you want to join the group “%(group_name)s”?')
    confirm_title = _('Join group “%(group_name)s”?')
    template_name = 'cosinnus/group_confirm.html'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(GroupUserJoinView, self).dispatch(request, *args, **kwargs)

    def confirm_action(self):
        CosinnusGroupMembership.objects.create(
            user=self.request.user,
            group=self.object,
            status=MEMBERSHIP_PENDING
        )

group_user_join = GroupUserJoinView.as_view()


class GroupUserLeaveView(GroupConfirmMixin, DetailView):

    confirm_label = _('Leave')
    confirm_question = _('Do you want to leave the group “%(group_name)s”?')
    confirm_title = _('Leaving group “%(group_name)s”?')
    submit_css_classes = 'btn-danger'
    template_name = 'cosinnus/group_confirm.html'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(GroupUserLeaveView, self).dispatch(request, *args, **kwargs)

    def confirm_action(self):
        admins = CosinnusGroupMembership.objects.get_admins(group=self.object)
        if len(admins) > 1 or self.request.user.pk not in admins:
            try:
                membership = CosinnusGroupMembership.objects.get(
                    user=self.request.user,
                    group=self.object,
                    status=MEMBERSHIP_MEMBER
                )
                membership.delete()
            except CosinnusGroupMembership.DoesNotExist:
                pass
        else:
            messages.error(self.request,
                _('You cannot leave this group. You are the only administrator left.')
            )

group_user_leave = GroupUserLeaveView.as_view()


class GroupUserWithdrawView(GroupConfirmMixin, DetailView):

    confirm_label = _('Withdraw')
    confirm_question = _('Do you want to withdraw your join request to the group “%(group_name)s”?')
    confirm_title = _('Withdraw join request to group “%(group_name)s”?')
    submit_css_classes = 'btn-danger'
    template_name = 'cosinnus/group_confirm.html'

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(GroupUserWithdrawView, self).dispatch(request, *args, **kwargs)

    def confirm_action(self):
        try:
            membership = CosinnusGroupMembership.objects.get(
                user=self.request.user,
                group=self.object,
                status=MEMBERSHIP_PENDING
            )
            membership.delete()
        except CosinnusGroupMembership.DoesNotExist:
            pass

group_user_withdraw = GroupUserWithdrawView.as_view()


class UserSelectMixin(object):

    form_class = MembershipForm
    model = CosinnusGroupMembership
    slug_field = 'user__username'
    slug_url_kwarg = 'username'
    template_name = 'cosinnus/group_user_form.html'

    def get_form_kwargs(self):
        kwargs = super(UserSelectMixin, self).get_form_kwargs()
        kwargs['group'] = self.group
        kwargs['user_qs'] = self.get_user_qs()
        return kwargs

    def get_initial(self):
        username = self.kwargs.get('username', None)
        if username:
            user = get_user_model()._default_manager.get(username=username)
            return {'user': user}

    def get_queryset(self):
        return self.model.objects.filter(group=self.group)

    def get_success_url(self):
        return reverse('cosinnus:group-detail', kwargs={'group': self.group.slug})


class GroupUserAddView(RequireAdminMixin, UserSelectMixin, CreateView):

    def form_valid(self, form):
        user = form.cleaned_data.get('user')
        status = form.cleaned_data.get('status')
        try:
            m = self.model.objects.get(user=user, group=self.group)
            m.status = status
            m.save(update_fields=['status'])
            return HttpResponseRedirect(self.get_success_url())
        except self.model.DoesNotExist:
            return super(GroupUserAddView, self).form_valid(form)

    def get_context_data(self, **kwargs):
        context = super(GroupUserAddView, self).get_context_data(**kwargs)
        context.update({
            'submit_label': _('Add'),
        })
        return context

    def get_user_qs(self):
        uids = self.model.objects.get_members(group=self.group)
        return get_user_model()._default_manager.exclude(id__in=uids)

group_user_add = GroupUserAddView.as_view()


class GroupUserUpdateView(RequireAdminMixin, UserSelectMixin, UpdateView):

    def form_valid(self, form):
        user = form.cleaned_data.get('user')
        current_status = self.get_object().status
        new_status = form.cleaned_data.get('status')
        if (len(self.group.admins) > 1 or not self.group.is_admin(user)):
            if user != self.request.user or self.request.user.is_superuser:
                return super(GroupUserUpdateView, self).form_valid(form)
            else:
                messages.error(self.request, _('You cannot change your own admin status.'))
        elif current_status == MEMBERSHIP_ADMIN and new_status != MEMBERSHIP_ADMIN:
            messages.error(self.request, _('You cannot remove “%(username)s” form '
                'this group. Only one admin left.') % {'username': user.username})
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super(GroupUserUpdateView, self).get_context_data(**kwargs)
        context.update({
            'submit_label': _('Save'),
        })
        return context

    def get_user_qs(self):
        return self.group.users

group_user_update = GroupUserUpdateView.as_view()


class GroupUserDeleteView(RequireAdminMixin, UserSelectMixin, DeleteView):

    template_name = 'cosinnus/group_confirm.html'

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        group = self.object.group
        user = self.object.user
        if (len(group.admins) > 1 or not group.is_admin(user)):
            if user != self.request.user or self.request.user.is_superuser:
                self.object.delete()
            else:
                messages.error(self.request, _('You cannot remove yourself from a group.'))
        else:
            messages.error(self.request, _('You cannot remove “%(username)s” form '
                'this group. Only one admin left.') % {'username': user.username})
        return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        context = super(GroupUserDeleteView, self).get_context_data(**kwargs)
        group_name = self.object.group.name
        context.update({
            'confirm_label': _('Delete'),
            'confirm_question': _('Do you want to remove the user “%(username)s”  from the group “%(group_name)s”?') % {
                'username': self.object.user.get_username(),
                'group_name': group_name,
            },
            'confirm_title': _('Remove user from group “%(group_name)s”?') % {
                'group_name': group_name,
            },
            'submit_css_classes': 'btn-danger',
        })
        return context

group_user_delete = GroupUserDeleteView.as_view()
