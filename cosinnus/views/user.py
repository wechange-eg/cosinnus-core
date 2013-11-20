# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from cosinnus.core.decorators.views import staff_required, superuser_required
from cosinnus.forms.user import UserForm


USER_MODEL = get_user_model()


class UserListView(ListView):

    model = USER_MODEL
    template_name = 'cosinnus/user_list.html'

user_list = UserListView.as_view()


class UserCreateView(CreateView):

    form_class = UserForm
    model = USER_MODEL
    success_url = reverse_lazy('cosinnus:user-list')
    template_name = 'cosinnus/user_form.html'

    @method_decorator(superuser_required)
    def dispatch(self, *args, **kwargs):
        return super(UserCreateView, self).dispatch(*args, **kwargs)

user_create = UserCreateView.as_view()


class UserDetailView(DetailView):

    model = USER_MODEL
    slug_field = 'username'
    slug_url_kwarg = 'username'
    template_name = 'cosinnus/user_detail.html'

    @method_decorator(staff_required)
    def dispatch(self, *args, **kwargs):
        return super(UserDetailView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UserDetailView, self).get_context_data(**kwargs)

        profile = context['user'].cosinnus_profile
        context['profile'] = profile
        context['optional_fields'] = profile.optional_fields

        return context

user_detail = UserDetailView.as_view()


class UserUpdateView(UpdateView):

    form_class = UserForm
    model = USER_MODEL
    slug_field = 'username'
    slug_url_kwarg = 'username'
    template_name = 'cosinnus/user_form.html'

    @method_decorator(staff_required)
    def dispatch(self, *args, **kwargs):
        return super(UserUpdateView, self).dispatch(*args, **kwargs)


user_update = UserUpdateView.as_view()
