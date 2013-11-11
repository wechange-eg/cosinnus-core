# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.utils.decorators import method_decorator
from django.views.generic import UpdateView
from django.views.generic.detail import SingleObjectMixin, DetailView

from cosinnus.forms.profile import UserProfileForm
from cosinnus.models.profile import get_user_profile_model


class UserProfileObjectMixin(SingleObjectMixin):
    model = get_user_profile_model()

    def get_object(self):
        return self.model._default_manager.get_for_user(self.request.user)

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(UserProfileObjectMixin, self).dispatch(
            request, *args, **kwargs)


class UserProfileDetailView(UserProfileObjectMixin, DetailView):
    template_name = 'cosinnus/userprofile_detail.html'

    def get_context_data(self, **kwargs):
        context = super(UserProfileDetailView, self).get_context_data(**kwargs)
        profile = context['object']
        context['optional_fields'] = profile.optional_fields
        return context

detail_view = UserProfileDetailView.as_view()


class UserProfileUpdateView(UserProfileObjectMixin, UpdateView):
    form_class = UserProfileForm
    template_name = 'cosinnus/userprofile_form.html'

    def get_success_url(self):
        return reverse('cosinnus:profile-detail')

update_view = UserProfileUpdateView.as_view()
