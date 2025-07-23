# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from builtins import str

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http.response import Http404, HttpResponseRedirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, UpdateView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import DeleteView

from cosinnus.core.decorators.views import redirect_to_error_page, redirect_to_not_logged_in
from cosinnus.forms.profile import UserProfileForm
from cosinnus.models.group import CosinnusGroup, CosinnusGroupMembership
from cosinnus.models.profile import get_user_profile_model
from cosinnus.models.tagged import BaseTagObject
from cosinnus.views.profile_deletion import deactivate_user_and_mark_for_deletion
from cosinnus.utils.permissions import (
    check_user_can_see_user,
    check_user_integrated_portal_member,
    check_user_superuser,
)
from cosinnus.utils.user import filter_active_users
from cosinnus.views.mixins.avatar import AvatarFormMixin


logger = logging.getLogger('cosinnus')


class UserProfileObjectMixin(SingleObjectMixin):
    model = get_user_profile_model()
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_object(self, queryset=None):
        """Return the userprofile for the current logged in user if no kwarg slug is given,
        or the userprofile for the username slug given"""

        pk = self.kwargs.get(self.pk_url_kwarg, None)
        slug = self.kwargs.get(self.slug_url_kwarg, None)

        # return the current user's userprofile if no slug is given
        if not pk and not slug:
            if not self.request.user.is_authenticated:
                return None
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
            raise AttributeError(
                'Generic detail view %s must be called with ' 'either an object pk or a slug.' % self.__class__.__name__
            )
        try:
            # Get the single item from the filtered queryset
            obj = queryset.get()
        except ObjectDoesNotExist:
            raise Http404(
                _('No %(verbose_name)s found matching the query') % {'verbose_name': queryset.model._meta.verbose_name}
            )

        return obj


class UserProfileDetailView(UserProfileObjectMixin, DetailView):
    template_name = 'cosinnus/user/userprofile_detail.html'

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        target_user_is_guest = False

        """ Check if the user can access the targeted user profile. """
        try:
            target_user_profile = self.get_object(self.get_queryset())
        except Http404:
            # check on an unfiltered queryset if we attempt to view a guest user
            qs = super().get_queryset()
            slug = self.kwargs.get(self.slug_url_kwarg, None)
            slug_field = self.get_slug_field()
            qs = qs.filter(**{'user__' + slug_field: slug})
            target_user_profile = qs.count() == 1 and qs[0] or None
            if target_user_profile and target_user_profile.user.is_guest:
                target_user_is_guest = True
            else:
                raise

        if not target_user_profile:
            return redirect_to_not_logged_in(request)
        target_user_visibility = target_user_profile.media_tag.visibility
        user = request.user
        # VISIBILITY_ALL users can always be seen, so skip the check
        if not target_user_visibility == BaseTagObject.VISIBILITY_ALL:
            # all other views require at least to be logged in
            if not user.is_authenticated:
                return redirect_to_not_logged_in(request)
            if not check_user_can_see_user(user, target_user_profile.user) and not target_user_is_guest:
                messages.warning(request, _('This profile is not visible to you due to its privacy settings.'))
                raise PermissionDenied

        if target_user_is_guest:
            messages.warning(
                request, _('User "%s" is a guest user and has no profile.') % target_user_profile.get_full_name()
            )
            return redirect_to_error_page(request, view=self)

        return super(UserProfileDetailView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        if not getattr(self, 'qs', None):
            qs = super(UserProfileDetailView, self).get_queryset()
            if not (self.request.GET.get('force_show', False) == '1' and check_user_superuser(self.request.user)):
                qs = filter_active_users(qs, filter_on_user_profile_model=True)
            self.qs = qs
        return self.qs

    def get_conferences_for_user(self, profile):
        if not settings.COSINNUS_CONFERENCES_ENABLED:
            return []

        from cosinnus.models.group_extra import CosinnusConference

        applications = profile.user.user_applications.all()
        conferences_application_ids = list(applications.values_list('conference__id', flat=True))
        conferences_membership_ids = [conference.id for conference in profile.cosinnus_conferences]
        unique_ids = set(conferences_application_ids + conferences_membership_ids)

        current_conferences = (
            CosinnusConference.objects.filter(id__in=list(unique_ids)).filter(to_date__gte=now()).order_by('from_date')
        )
        ended_conferences = (
            CosinnusConference.objects.filter(id__in=list(unique_ids))
            .exclude(to_date__gte=now())
            .order_by('-from_date')
        )

        conferences = list(current_conferences) + list(ended_conferences)
        return conferences

    def get_context_data(self, **kwargs):
        context = super(UserProfileDetailView, self).get_context_data(**kwargs)
        profile = context['object']
        context.update(
            {
                'optional_fields': profile.get_optional_fields(),
                'profile': profile,
                'this_user': profile.user,
                'conferences': self.get_conferences_for_user(profile),
            }
        )
        return context


detail_view = UserProfileDetailView.as_view()


class UserProfileUpdateView(AvatarFormMixin, UserProfileObjectMixin, UpdateView):
    form_class = UserProfileForm
    template_name = 'cosinnus/user/userprofile_form.html'
    message_success = _('Your profile was edited successfully.')

    # for extending views, changes some behaviour with the mode that an admin is doing direct changes
    # (e.g. no validation for e-mail changes)
    is_admin_elevated_view = False

    # if set to True, all fields will always be kept enabled
    # if set to False, disables some fields depending on settings variables
    disable_conditional_field_locking = False

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(UserProfileObjectMixin, self).dispatch(request, *args, **kwargs)

    def get_initial(self):
        """Allow pre-populating managed tags on userprofile edit from initial default tags"""
        initial = super().get_initial()
        if settings.COSINNUS_MANAGED_TAGS_ENABLED and (
            (settings.COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_SELF and settings.COSINNUS_MANAGED_TAGS_IN_UPDATE_FORM)
            or settings.COSINNUS_MANAGED_TAGS_ASSIGNABLE_IN_USER_ADMIN_FORM
        ):
            if settings.COSINNUS_MANAGED_TAGS_DEFAULT_INITIAL_SLUG is not None:
                initial['managed_tag_field'] = settings.COSINNUS_MANAGED_TAGS_DEFAULT_INITIAL_SLUG
        return initial

    def get_success_url(self):
        return reverse('cosinnus:profile-detail')

    def post(self, request, *args, **kwargs):
        """if user changed his email, check if user is member of an integrated portal,
        and if so ignore that change. Also, ignore the change if email verification is active, and instead
        set a new email-to-be-verified and send user a confirmation email."""
        self.object = self.get_object()
        user = self.object.user
        if request.POST.get('user-email', user.email) != user.email and check_user_integrated_portal_member(user):
            messages.warning(
                request,
                _(
                    "Your user account is associated with an integrated Portal. This account's email address is fixed "
                    'and therefore was left unchanged.'
                ),
            )
            request.POST._mutable = True
            request.POST['user-email'] = user.email
        elif not self.is_admin_elevated_view and request.POST.get('user-email', user.email) != user.email:
            # do not accept any e-mail changes (from fudged forms) on this form for regular users,
            # only for the admin elevated view!
            request.POST._mutable = True
            request.POST['user-email'] = user.email

        return super(UserProfileUpdateView, self).post(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            ret = super(UserProfileUpdateView, self).form_valid(form)
            messages.success(self.request, self.message_success)
        except AttributeError as e:
            if str(e) == "'dict' object has no attribute '_committed'":
                # here we couldn't save the avatar
                messages.error(
                    self.request,
                    _('Sorry, your profile could not be saved because there was an error while processing the avatar!'),
                )
            else:
                messages.error(self.request, _('Sorry, something went wrong while saving your profile!'))
            ret = HttpResponseRedirect(reverse('cosinnus:profile-edit'))
        return ret

    def get_form(self, *args, **kwargs):
        form = super(UserProfileUpdateView, self).get_form(*args, **kwargs)
        # note: we have a django-multiforms form here with 'user', 'obj' (CosinnusProfile) and 'media_tag'!

        if not self.disable_conditional_field_locking:
            for form_name, formfield_list in settings.COSINNUS_USERPROFILE_DISABLED_FIELDS.items():
                sub_form = form.forms[form_name]
                # disable profile formfields from settings
                # we also need to remove any validation errors from required later-disabled fields
                for field_name in formfield_list:
                    if field_name in sub_form.fields:
                        field = sub_form.fields[field_name]
                        field.disabled = True
                        field.required = False
            # disable the userprofile visibility field if it is locked
            if settings.COSINNUS_USERPROFILE_VISIBILITY_SETTINGS_LOCKED is not None:
                field = form.forms['media_tag'].fields['visibility']
                field.disabled = True
                field.required = False

        # disable all fields that require a certain managed_tag to be assigned to the user
        # that this user doesn't have
        user_managed_tag_slugs = [tag.slug for tag in self.object.get_managed_tags() if tag]
        for tag_slug_list, field_list in settings.COSINNUS_USERPROFILE_EXTRA_FIELDS_ONLY_ENABLED_FOR_MANAGED_TAGS:
            if not any([tag_slug in user_managed_tag_slugs for tag_slug in tag_slug_list]):
                for field_name in field_list:
                    if field_name in form.forms['obj'].fields:
                        field = form.forms['obj'].fields[field_name]
                        field.disabled = True
                        field.required = False

        # disable the email field for any normal views,
        # but keep it enabled for the elevated admin view
        if not self.is_admin_elevated_view:
            field = form.forms['user'].fields['email']
            field.disabled = True
            field.required = False

        return form

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super(UserProfileUpdateView, self).get_form_kwargs(*args, **kwargs)
        if getattr(settings, 'COSINNUS_MANAGED_TAGS_ENABLED', False):
            form_kwargs.update(
                {
                    'obj__is_profile_update': True,
                }
            )
        return form_kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {
                'is_admin_elevated_view': self.is_admin_elevated_view,
            }
        )
        return context


update_view = UserProfileUpdateView.as_view()


class UserProfileDeleteView(AvatarFormMixin, UserProfileObjectMixin, DeleteView):
    # form_class = UserProfileForm
    template_name = 'cosinnus/user/userprofile_delete.html'
    message_success = _(
        "Your user account has been deactivated and will be deleted in 30 days. We're sorry you are no longer with us."
    )

    @method_decorator(login_required)
    def dispatch(self, request, *args, **kwargs):
        return super(UserProfileDeleteView, self).dispatch(request, *args, **kwargs)

    def get_success_url(self):
        # param `message=userDeactivated` is used as a flag for the v3 frontend to display an info message like
        # `message_success` on the login screen. it is non-functional and ignored in the django frontend.
        return reverse('login') + '?message=userDeactivated'

    def _validate_user_delete_safe(self, user):
        is_safe = user.is_authenticated

        non_safe_groups = []
        for group in CosinnusGroup.objects.get_for_user(user):
            admins = CosinnusGroupMembership.objects.get_admins(group=group)
            if [user.pk] == admins:
                non_safe_groups.append(group)
                is_safe = False
        if non_safe_groups:
            msg = _(
                'You are the only administrator left for these projects, groups or conferences. Please appoint a '
                'different administrator or delete them first:'
            )
            group_string = ''.join([f'\n* {group.name}' for group in non_safe_groups])
            msg = f'{msg}\n{group_string}'
            messages.error(self.request, msg)
        return is_safe

    def get(self, request, *args, **kwargs):
        self._validate_user_delete_safe(self.request.user)
        return super(UserProfileDeleteView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if not self._validate_user_delete_safe(request.user):
            return HttpResponseRedirect(reverse('cosinnus:profile-delete'))

        # this no longer immediately deletes the user profile, but instead deactivates it!
        # function after 30 days.
        deactivate_user_and_mark_for_deletion(request.user, triggered_by_self=True)

        # log user out
        logout(request)
        messages.success(self.request, self.message_success)

        return HttpResponseRedirect(self.get_success_url())


delete_view = UserProfileDeleteView.as_view()
