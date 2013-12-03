# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import DetailView, FormView, ListView

from cosinnus.core.decorators.views import require_admin_access
from cosinnus.models import CosinnusGroup
from cosinnus.views.mixins.group import RequireAdminMixin, RequireReadMixin


class GroupListView(ListView):

    model = CosinnusGroup
    template_name = 'cosinnus/group_list.html'

    def get_queryset(self):
        if self.request.user.is_authenticated():
            return self.model.objects.all()
        else:
            return self.model.objects.public().all()

group_list = GroupListView.as_view()


class GroupDetailView(RequireReadMixin, DetailView):

    group_filter_kwarg = None
    model = CosinnusGroup
    template_name = 'cosinnus/group_detail.html'

    def get_object(self, queryset=None):
        return self.group

    def get_context_data(self, **kwargs):
        context = super(GroupDetailView, self).get_context_data(**kwargs)
        users = self.group.users.order_by('first_name', 'last_name').select_related('cosinnus_profile')
        context['users'] = users
        return context

group_detail = GroupDetailView.as_view()


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

    @require_admin_access()
    def dispatch(self, request, *args, **kwargs):
        return super(GroupUserDeleteView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        user = get_object_or_404(get_user_model(), username=kwargs.get('username'))
        self.group.users.remove(user)
        return HttpResponse(status=200)

group_user_delete = GroupUserDeleteView.as_view()
