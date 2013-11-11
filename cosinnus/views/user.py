# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DetailView, ListView, View

from cosinnus.decorators.views import require_admin_group, staff_required
from cosinnus.views.mixins import RequireGroupMixin
from cosinnus.forms.authentication import UserForm


USER_MODEL = get_user_model()


class UserAddGroupView(View):
    # TODO: I don't like this solution yet. Even though enforcing POST
    # requests, I think I'm missing some security concerns. We'd better use a
    # FormView

    http_method_names = ['post']

    @require_admin_group()
    def dispatch(self, request, *args, **kwargs):
        return super(UserAddGroupView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, pk=kwargs.get('group'))
        user = get_object_or_404(USER_MODEL, pk=kwargs.get('user'))
        group.user_set.add(user)
        return HttpResponse(status=200)

user_add_group = UserAddGroupView.as_view()


class UserCreateView(RequireGroupMixin, CreateView):

    model = USER_MODEL
    form_class = UserForm

    @require_admin_group()
    def dispatch(self, *args, **kwargs):
        return super(UserCreateView, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        self.object = form.save()
        self.group.user_set.add(self.object)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('sinn_auth-user-list', kwargs={'group': self.group.pk})

user_create = UserCreateView.as_view()


class UserDetailView(RequireGroupMixin, DetailView):

    model = USER_MODEL

    @method_decorator(staff_required)
    def dispatch(self, *args, **kwargs):
        return super(UserDetailView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UserDetailView, self).get_context_data(**kwargs)

        profile = context['user'].get_profile()
        context['profile'] = profile
        context['optional_fields'] = profile.get_optional_fields()

        return context

user_detail = UserDetailView.as_view()


class UserListView(RequireGroupMixin, ListView):

    model = USER_MODEL

    @require_admin_group()
    def dispatch(self, *args, **kwargs):
        return super(UserListView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UserListView, self).get_context_data(**kwargs)
        # Set membership status
        group_members = self.group.user_set.all()
        context['users'] = [{
            "user": o,
            "in_group": (o in group_members),
        } for o in context["object_list"].order_by("username")]

        return context

user_list = UserListView.as_view()


class UserRemoveGroupView(View):
    # TODO: I don't like this solution yet. Even though enforcing POST
    # requests, I think I'm missing some security concerns. We'd better use a
    # FormView

    http_method_names = ['post']

    @require_admin_group()
    def dispatch(self, request, *args, **kwargs):
        return super(UserRemoveGroupView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        group = get_object_or_404(Group, pk=kwargs.get('group'))
        user = get_object_or_404(USER_MODEL, pk=kwargs.get('user'))
        group.user_set.remove(user)
        return HttpResponse(status=200)

user_remove_group = UserRemoveGroupView.as_view()
