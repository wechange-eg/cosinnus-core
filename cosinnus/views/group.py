# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, FormView, ListView

from cosinnus.core.decorators.views import require_admin_group
from cosinnus.views.mixins.group import RequireGroupMixin


class GroupListView(ListView):

    model = Group
    template_name = 'cosinnus/group_list.html'

    def dispatch(self, *args, **kwargs):
        return super(GroupListView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(GroupListView, self).get_context_data(**kwargs)
        user = self.request.user
        context['user'] = user
        return context

group_list = GroupListView.as_view()


class GroupDetailView(RequireGroupMixin, DetailView):

    group_filter_kwarg = None
    model = Group
    template_name = 'cosinnus/group_detail.html'

    def get_object(self, queryset=None):
        return self.group

    def get_context_data(self, **kwargs):
        context = super(GroupDetailView, self).get_context_data(**kwargs)
        users = self.group.user_set.order_by('first_name', 'last_name')
        context.update({'users': users})
        return context

group_detail = GroupDetailView.as_view()


class GroupUserListView(RequireGroupMixin, ListView):

    template_name = 'cosinnus/group_user_list.html'

    def get_queryset(self):
        return self.group.user_set.all()

group_user_list = GroupUserListView.as_view()


class GroupUserAddView(RequireGroupMixin, FormView):
    # TODO: I don't like this solution yet. Even though enforcing POST
    # requests, I think I'm missing some security concerns. We'd better use a
    # FormView

    http_method_names = ['post']

    @require_admin_group()
    def dispatch(self, request, *args, **kwargs):
        return super(GroupUserAddView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        user = get_object_or_404(get_user_model(), username=kwargs.get('username'))
        self.group.user_set.add(user)
        return HttpResponse(status=200)

group_user_add = GroupUserAddView.as_view()


class GroupUserDeleteView(RequireGroupMixin, FormView):
    # TODO: I don't like this solution yet. Even though enforcing POST
    # requests, I think I'm missing some security concerns. We'd better use a
    # FormView

    http_method_names = ['post']

    @require_admin_group()
    def dispatch(self, request, *args, **kwargs):
        return super(GroupUserDeleteView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        user = get_object_or_404(get_user_model(), username=kwargs.get('username'))
        self.group.user_set.remove(user)
        return HttpResponse(status=200)

group_user_delete = GroupUserDeleteView.as_view()
