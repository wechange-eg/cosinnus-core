# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model, login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.urlresolvers import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from cosinnus.core.decorators.views import staff_required, superuser_required
from cosinnus.forms.user import UserCreationForm, UserChangeForm
from cosinnus.views.mixins.ajax import patch_body_json_data
from cosinnus.utils.http import JSONResponse
from django.contrib import messages



USER_MODEL = get_user_model()


class UserListView(ListView):

    model = USER_MODEL
    template_name = 'cosinnus/user/user_list.html'

user_list = UserListView.as_view()


class UserCreateView(CreateView):

    form_class = UserCreationForm
    model = USER_MODEL
    success_url = reverse_lazy('login')
    template_name = 'cosinnus/registration/signup.html'

    message_success = _('User "%(user)s" was registered successfully. You can now log in using this username.')
    
    def form_valid(self, form):
        ret = super(UserCreateView, self).form_valid(form)
        messages.success(self.request,
            self.message_success % {'user': self.object.username})
        return ret

    def dispatch(self, *args, **kwargs):
        return super(UserCreateView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UserCreateView, self).get_context_data(**kwargs)
        context['submit_label'] = _('Create')
        return context

user_create = UserCreateView.as_view()


class UserDetailView(DetailView):

    model = USER_MODEL
    slug_field = 'username'
    slug_url_kwarg = 'username'
    template_name = 'cosinnus/user/userprofile_detail.html'

    @method_decorator(staff_required)
    def dispatch(self, *args, **kwargs):
        return super(UserDetailView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UserDetailView, self).get_context_data(**kwargs)

        profile = context['user'].cosinnus_profile
        context['profile'] = profile
        context['optional_fields'] = profile.get_optional_fields()

        return context

user_detail = UserDetailView.as_view()


class UserUpdateView(UpdateView):

    form_class = UserChangeForm
    model = USER_MODEL
    slug_field = 'username'
    slug_url_kwarg = 'username'
    template_name = 'cosinnus/registration/signup.html'

    @method_decorator(staff_required)
    def dispatch(self, *args, **kwargs):
        return super(UserUpdateView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UserUpdateView, self).get_context_data(**kwargs)
        context['submit_label'] = _('Save')
        return context

    def get_success_url(self):
        return reverse('cosinnus:user-detail',
            kwargs={'username': self.object.username})

user_update = UserUpdateView.as_view()


@sensitive_post_parameters()
@csrf_protect
@never_cache
def login_api(request, authentication_form=AuthenticationForm):
    """
    Logs the user specified by the `authentication_form` in.
    """
    if request.method == "POST":
        request = patch_body_json_data(request)

        # TODO: Django<=1.5: Django 1.6 removed the cookie check in favor of CSRF
        request.session.set_test_cookie()

        form = authentication_form(request, data=request.POST)
        if form.is_valid():
            auth_login(request, form.get_user())
            return JSONResponse({})
        else:
            return JSONResponse(form.errors, status=401)
    else:
        return JSONResponse({}, status=405)  # Method not allowed


def logout_api(request):
    """
    Logs the user out.
    """
    auth_logout(request)
    return JSONResponse({})
