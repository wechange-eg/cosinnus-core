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
from django.core.exceptions import ObjectDoesNotExist
from django.http.response import Http404


class UserProfileObjectMixin(SingleObjectMixin):
    model = get_user_profile_model()
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_object(self, queryset=None):
        """ Return the userprofile for the current logged in user if no kwarg slug is given,
            or the userprofile for the username slug given """
        
        pk = self.kwargs.get(self.pk_url_kwarg, None)
        slug = self.kwargs.get(self.slug_url_kwarg, None)
        
        # return the current user's userprofile if no slug is given
        if not pk and not slug:
            return self.model._default_manager.get_for_user(self.request.user)
        
        if queryset is None:
            queryset = self.get_queryset()
        if pk is not None:
            queryset = queryset.filter(user__pk=pk)
        # Next, try looking up by slug.
        elif slug is not None:
            slug_field = self.get_slug_field()
            queryset = queryset.filter(**{'user__' + slug_field: slug})
        # If none of those are defined, it's an error.
        else:
            raise AttributeError("Generic detail view %s must be called with "
                                 "either an object pk or a slug."
                                 % self.__class__.__name__)
        try:
            # Get the single item from the filtered queryset
            obj = queryset.get()
        except ObjectDoesNotExist:
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})
        
        return obj


class UserProfileDetailView(UserProfileObjectMixin, DetailView):
    template_name = 'cosinnus/user/userprofile_detail.html'

    def get_context_data(self, **kwargs):
        context = super(UserProfileDetailView, self).get_context_data(**kwargs)
        profile = context['object']
        context.update({
            'optional_fields': profile.get_optional_fields(),
            'profile': profile,
            'this_user': profile.user,
        })
        return context

detail_view = UserProfileDetailView.as_view()


class UserProfileUpdateView(AvatarFormMixin, UserProfileObjectMixin, UpdateView):
    form_class = UserProfileForm
    template_name = 'cosinnus/user/userprofile_form.html'
    message_success = _('Your profile was edited successfully.')
    
    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(UserProfileObjectMixin, self).dispatch(
            request, *args, **kwargs)

    def get_success_url(self):
        return reverse('cosinnus:profile-detail')
    
    def form_valid(self, form):
        ret = super(UserProfileUpdateView, self).form_valid(form)
        messages.success(self.request, self.message_success)
        return ret

update_view = UserProfileUpdateView.as_view()
