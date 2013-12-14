# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.generic import (CreateView, DeleteView, DetailView, FormView,
    ListView, UpdateView)

from cosinnus.core.decorators.views import superuser_required
from cosinnus.forms.group import CosinnusGroupForm
from cosinnus.models import CosinnusGroup, CosinnusGroupMembership
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


class GroupUserAddView(RequireAdminMixin, FormView):
    # TODO: I don't like this solution yet. Even though enforcing POST
    # requests, I think I'm missing some security concerns. We'd better use a
    # FormView

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        user = get_object_or_404(get_user_model(), username=kwargs.get('username'))
        self.group.users.add(user)
        return HttpResponse(status=200)

group_user_add = GroupUserAddView.as_view()


class GroupUserDeleteView(RequireAdminMixin, FormView):
    # TODO: I don't like this solution yet. Even though enforcing POST
    # requests, I think I'm missing some security concerns. We'd better use a
    # FormView

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        user = get_object_or_404(get_user_model(), username=kwargs.get('username'))
        self.group.users.remove(user)
        return HttpResponse(status=200)

group_user_delete = GroupUserDeleteView.as_view()
