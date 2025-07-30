# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from builtins import str
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http.response import Http404, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.decorators import method_decorator
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.views import View
from django.views.generic import DetailView, UpdateView
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import DeleteView
from oauth2_provider import models as oauth2_provider_models

from cosinnus.core import signals
from cosinnus.core.decorators.views import redirect_to_error_page, redirect_to_not_logged_in
from cosinnus.core.mail import send_html_mail
from cosinnus.forms.profile import UserProfileForm
from cosinnus.models.group import CosinnusGroup, CosinnusGroupMembership
from cosinnus.models.profile import UserBlock, get_user_profile_model
from cosinnus.models.tagged import BaseTagObject, get_tag_object_model
from cosinnus.models.widget import WidgetConfig
from cosinnus.templatetags.cosinnus_tags import full_name, textfield
from cosinnus.utils.permissions import (
    check_user_can_see_user,
    check_user_integrated_portal_member,
    check_user_superuser,
)
from cosinnus.utils.user import filter_active_users
from cosinnus.views.mixins.avatar import AvatarFormMixin
from cosinnus.views.mixins.group import RequireLoggedInMixin

logger = logging.getLogger('cosinnus')


def deactivate_user(user):
    """Deactivates a user account"""
    user.is_active = False
    user.save()
    # save the user's profile as well,
    # as numerous triggers occur on the profile instead of the user object
    if user.cosinnus_profile:
        user.cosinnus_profile.save()


def deactivate_user_and_mark_for_deletion(user, triggered_by_self=False):
    """Deacitvates a user account and marks them for deletion in 30 days"""
    if hasattr(user, 'cosinnus_profile') and user.cosinnus_profile:
        # add a marked-for-deletion flag and a cronjob, deleting the profile using this
        deletion_schedule_time = now() + timedelta(days=settings.COSINNUS_USER_PROFILE_DELETION_SCHEDULE_DAYS)
        user.cosinnus_profile.scheduled_for_deletion_at = deletion_schedule_time
        user.cosinnus_profile.deletion_triggered_by_self = triggered_by_self
        user.cosinnus_profile.save()
    deactivate_user(user)

    # send extended deactivation signal
    signals.user_deactivated_and_marked_for_deletion.send(sender=None, profile=user.cosinnus_profile)


def delete_guest_user(user, deactivate_only=True):
    """Deletes a user account (permanently or deactivate only) if they are a guest user.
    Used when a guest user account is no longer needed (after logout) or when it has become
    invalid (when the token or group it belongs to have been deleted).

    @param deactivate_only: if True, the guest account will only be disabled, which will still lead to
        the session becoming unusable. if False, the account will be irrevocably deleted."""
    if user.is_guest:
        if deactivate_only:
            user.is_active = False
            user.save()
        else:
            user.delete()


def reactivate_user(user):
    """Reactivates a user account and deletes their marked-for-deletion-flag"""
    user.is_active = True
    user.save()
    # save the user's profile as well,
    # as numerous triggers occur on the profile instead of the user object
    if user.cosinnus_profile:
        # delete the marked-for-deletion flag
        user.cosinnus_profile.scheduled_for_deletion_at = None
        user.cosinnus_profile.deletion_triggered_by_self = False
        user.cosinnus_profile.save()
    else:
        # create a new userprofile if the old one was already deleted,
        # so we have a functioning user account again
        get_user_profile_model()._default_manager.get_for_user(user)


def delete_userprofile(user):
    """Deactivate and completely anonymize a user's profile, name and email,
    leaving only the empty User object.
    All content created by the user and foreign-key relations are preserved,
    but will display ""Deleted User)" as creator.
    Will not work on userprofiles whose user account is still active!"""

    if user.is_active:
        logger.warning(
            'Aborting user profile deletion because the user account was still active!', extra={'user_id': user.id}
        )
        return

    profile = user.cosinnus_profile

    # send deletion signal
    signals.pre_userprofile_delete.send(sender=None, profile=profile)

    # delete user widgets
    widgets = WidgetConfig.objects.filter(user_id__exact=user.pk)
    for widget in widgets:
        widget.delete()

    # leave all groups
    for membership in CosinnusGroupMembership.objects.filter(user=user):
        membership.delete()

    # delete user media_tag
    try:
        if profile.media_tag:
            profile.media_tag.delete()
    except get_tag_object_model().DoesNotExist:
        pass

    # delete AllAuth user data
    if settings.COSINNUS_IS_OAUTH_CLIENT:
        from allauth.account.models import EmailAddress
        from allauth.socialaccount.models import SocialAccount

        SocialAccount.objects.filter(user=user).delete()
        EmailAddress.objects.filter(user=user).delete()

    # delete oauth2_provider user tokens and grants
    try:
        oauth2_provider_models.get_grant_model().objects.filter(user=user).delete()
        oauth2_provider_models.get_access_token_model().objects.filter(user=user).delete()
        oauth2_provider_models.get_refresh_token_model().objects.filter(user=user).delete()
    except Exception as e:
        logger.warn(
            "Userprofile delete: could not delete a user's oauth tokens because of an exception.",
            extra={'exception': e},
        )

    # delete user profile
    if profile.avatar:
        profile.avatar.delete(False)
    profile.delete()

    # set user to inactive and anonymize all data.
    user.first_name = 'deleted'
    user.last_name = 'user'
    user.username = user.id
    # replace e-mail with random address
    user.email = '__deleted_user__%s@deleted.com' % get_random_string(length=12)

    # we no longer retain a padded version of the user's email
    # scramble_cutoff = user._meta.get_field('email').max_length - len(scrambled_email_prefix) - 2
    # scrambled_email_prefix = scrambled_email_prefix[:scramble_cutoff]

    user.is_active = False
    user.save()


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
        is_blocked = False
        if settings.COSINNUS_ENABLE_USER_BLOCK and self.request.user.is_authenticated:
            is_blocked = UserBlock.objects.filter(user=self.request.user, blocked_user=profile.user).exists()
        context.update(
            {
                'optional_fields': profile.get_optional_fields(),
                'profile': profile,
                'this_user': profile.user,
                'user_is_blocked': is_blocked,
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

        # send a notification email ignoring notification settings
        text = _(
            'Your platform profile stored with us under this email has been deactivated by you and was approved for '
            'deletion. The profile has been removed from the website and we will delete the account completely in 30 '
            'days.\n\nIf this has happened without your knowledge or if you change your mind in the meantime, please '
            'contact the portal administrators or the email address given in our imprint. Please note that the '
            'response time by e-mail may take longer in some cases. Please contact us as soon as possible if you would '
            'like to keep your profile.'
        )
        body_text = textfield(text)
        send_html_mail(
            request.user, _('Information about the deletion of your user account'), body_text, threaded=False
        )

        # this no longer immediately deletes the user profile, but instead deactivates it!
        # function after 30 days.
        deactivate_user_and_mark_for_deletion(request.user, triggered_by_self=True)

        # log user out
        logout(request)
        messages.success(self.request, self.message_success)

        return HttpResponseRedirect(self.get_success_url())


delete_view = UserProfileDeleteView.as_view()


class UserBlockViewMixin(object):
    http_method_names = ['post']

    def dispatch(self, request, username, *args, **kwargs):
        return super().dispatch(request, username, *args, **kwargs)

    def post(self, request, username, *args, **kwargs):
        username = username.strip()
        try:
            target_user = get_user_model().objects.get(username=username)
        except Exception:
            target_user = None
        if not target_user:
            messages.error(request, _('The user was not found.'))
            return redirect_to_error_page(request)

        success = False
        try:
            self.do_block_action(target_user)
            success = True
        except Exception as e:
            logger.warning(
                'An error occured when trying to block/unblock a user.',
                extra={'exception': e, 'target_user_id': target_user.id},
            )

        if success:
            messages.success(request, self.success_message % full_name(target_user))
            return redirect('cosinnus:profile-detail', username=username)
        else:
            messages.error(request, self.error_message % username)
            return redirect_to_error_page(request)

    def do_block_action(self, target_user):
        """Stub, implement block or unblock"""
        pass


class CosinnusUserBlockView(RequireLoggedInMixin, UserBlockViewMixin, View):
    """Marks a user as blocked for the current user.
    Note: you *can* in principle block inactive users! (Leaving this functionality to hide deleted user posts)."""

    success_message = _('User %s is now blocked.')
    error_message = _('There was an error blocking user %s.')

    def do_block_action(self, target_user):
        """Block the user"""
        UserBlock.block_user(self.request.user, target_user)


user_block_view = CosinnusUserBlockView.as_view()


class CosinnusUserUnblockView(RequireLoggedInMixin, UserBlockViewMixin, View):
    """Marks a user as unblocked for the current user.
    Note: you *can* in principle block inactive users! (Leaving this functionality to hide deleted user posts)."""

    success_message = _('User %s is no longer blocked.')
    error_message = _('There was an error unblocking user %s.')

    def do_block_action(self, target_user):
        """Unblock the user"""
        UserBlock.unblock_user(self.request.user, target_user)


user_unblock_view = CosinnusUserUnblockView.as_view()
