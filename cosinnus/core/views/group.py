# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.models import Group
from django.utils.decorators import method_decorator
from django.views.generic import DetailView, ListView

from cosinnus.core.decorators.views import staff_required
from cosinnus.core.views.mixins.group import RequireGroupMixin


class GroupDetailView(RequireGroupMixin, DetailView):

    group_filter_kwarg = None
    model = Group

    def get_object(self, queryset=None):
        return self.group

    def get_context_data(self, **kwargs):
        context = super(GroupDetailView, self).get_context_data(**kwargs)
        users = self.group.user_set.order_by('first_name', 'last_name')
        context.update({'users': users})
        return context

group_detail = GroupDetailView.as_view()


class GroupListView(ListView):

    model = Group

    @method_decorator(staff_required)
    def dispatch(self, *args, **kwargs):
        return super(GroupListView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(GroupListView, self).get_context_data(**kwargs)

        user = self.request.user
        context['user'] = user

        return context

group_list = GroupListView.as_view()
