# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.utils.decorators import method_decorator
from django.views.generic import UpdateView
from django.views.generic.detail import SingleObjectMixin, DetailView

from cosinnus.forms.profile import UserProfileForm
from cosinnus.models.profile import UserProfile


class UserProfileObjectMixin(SingleObjectMixin):
    model = UserProfile

    def get_object(self):
        return self.request.user.get_profile()

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(UserProfileObjectMixin, self).dispatch(
            request, *args, **kwargs)


class UserProfileDetailView(UserProfileObjectMixin, DetailView):
    def get_context_data(self, **kwargs):
        context = super(UserProfileDetailView, self).get_context_data(**kwargs)
        profile = context['userprofile']
        context['optional_fields'] = profile.get_optional_fields()
        return context

detail_view = UserProfileDetailView.as_view()


class UserProfileUpdateView(UserProfileObjectMixin, UpdateView):
    form_class = UserProfileForm

    def get_success_url(self):
        return reverse('cosinnus:profile-detail')

update_view = UserProfileUpdateView.as_view()
