# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView, UpdateView
from django.views.generic.detail import SingleObjectMixin

from cosinnus.forms.profile import UserProfileForm
from cosinnus.models.profile import get_user_profile_model
from cosinnus.views.mixins.avatar import AvatarFormMixin
from django.contrib import messages


class UserProfileObjectMixin(SingleObjectMixin):
    model = get_user_profile_model()

    def get_object(self):
        return self.model._default_manager.get_for_user(self.request.user)

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(UserProfileObjectMixin, self).dispatch(
            request, *args, **kwargs)


class UserProfileDetailView(UserProfileObjectMixin, DetailView):
    template_name = 'cosinnus/user/userprofile_detail.html'

    def get_context_data(self, **kwargs):
        context = super(UserProfileDetailView, self).get_context_data(**kwargs)
        profile = context['object']
        context['optional_fields'] = profile.get_optional_fields()
        return context

detail_view = UserProfileDetailView.as_view()


class UserProfileUpdateView(AvatarFormMixin, UserProfileObjectMixin, UpdateView):
    form_class = UserProfileForm
    template_name = 'cosinnus/user/userprofile_form.html'
    message_success = _('Your profile was edited successfully.')

    def get_success_url(self):
        return reverse('cosinnus:user-dashboard')
    
    def form_valid(self, form):
        ret = super(UserProfileUpdateView, self).form_valid(form)
        messages.success(self.request, self.message_success)
        return ret

update_view = UserProfileUpdateView.as_view()
