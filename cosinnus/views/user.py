# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from builtins import str
from copy import copy
from uuid import uuid1, uuid4

from annoying.functions import get_object_or_None
from django.contrib import messages
from django.contrib.auth import get_user_model, login
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.signals import user_logged_in
from django.contrib.auth.views import PasswordChangeView, PasswordResetConfirmView, PasswordResetView
from django.core.exceptions import ImproperlyConfigured, PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.dispatch.dispatcher import receiver
from django.http import Http404
from django.http.response import (
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
    HttpResponseRedirect,
    HttpResponseServerError,
    JsonResponse,
)
from django.shortcuts import redirect, render
from django.template import loader
from django.template.loader import render_to_string
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.translation import get_language
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView, DetailView, ListView, UpdateView
from django.views.generic.base import TemplateView
from django.views.generic.edit import FormView
from django_select2.views import NO_ERR_RESP, Select2View
from honeypot.decorators import check_honeypot

from cosinnus import cosinnus_notifications
from cosinnus.conf import settings
from cosinnus.core import signals
from cosinnus.core.decorators.views import (
    redirect_to_403,
    redirect_to_error_page,
    redirect_to_not_logged_in,
    staff_required,
)
from cosinnus.core.mail import (
    get_common_mail_context,
    send_html_mail_threaded,
    send_mail_or_fail,
    send_mail_or_fail_threaded,
)
from cosinnus.core.signals import user_logged_in_first_time, userprofile_created
from cosinnus.forms.user import (
    TermsOfServiceFormFields,
    UserChangeEmailFormWithPasswordValidation,
    UserChangeForm,
    UserCreationForm,
    UserGroupGuestAccessForm,
    ValidatedPasswordChangeForm,
)
from cosinnus.models import MEMBER_STATUS, MEMBERSHIP_INVITED_PENDING
from cosinnus.models.group import (
    CosinnusGroupInviteToken,
    CosinnusGroupMembership,
    CosinnusPortal,
    CosinnusUnregisterdUserGroupInvite,
    UserGroupGuestAccess,
)
from cosinnus.models.group_extra import CosinnusConference, CosinnusProject, CosinnusSociety
from cosinnus.models.membership import MEMBERSHIP_MEMBER
from cosinnus.models.profile import (
    PROFILE_SETTING_EMAIL_TO_VERIFY,
    PROFILE_SETTING_EMAIL_VERFICIATION_TOKEN,
    PROFILE_SETTING_FIRST_LOGIN,
    PROFILE_SETTING_LOGIN_TOKEN_SENT,
    PROFILE_SETTING_PASSWORD_NOT_SET,
    GlobalBlacklistedEmail,
    GlobalUserNotificationSetting,
    get_user_profile_model,
)
from cosinnus.models.tagged import BaseTagObject
from cosinnus.templatetags.cosinnus_tags import full_name, full_name_force, textfield
from cosinnus.utils.functions import is_email_valid
from cosinnus.utils.group import get_cosinnus_group_model, get_default_user_group_slugs
from cosinnus.utils.html import render_html_with_variables
from cosinnus.utils.permissions import (
    check_user_can_see_user,
    check_user_integrated_portal_member,
    check_user_superuser,
    check_user_verified,
)
from cosinnus.utils.tokens import email_blacklist_token_generator
from cosinnus.utils.urls import group_aware_reverse, redirect_next_or, redirect_with_next
from cosinnus.utils.user import (
    accept_user_tos_for_portal,
    create_guest_user_and_login,
    filter_active_users,
    get_group_select2_pills,
    get_newly_registered_user_email,
    get_user_by_email_safe,
    get_user_from_set_password_token,
    get_user_query_filter_for_search_terms,
    get_user_select2_pills,
)
from cosinnus.views.mixins.group import EndlessPaginationMixin, RequireLoggedInMixin

logger = logging.getLogger('cosinnus')

USER_MODEL = get_user_model()


def email_portal_admins(subject, template, data):
    admins = get_user_model().objects.filter(id__in=CosinnusPortal.get_current().admins)
    text = textfield(render_to_string('cosinnus/mail/user_register_notification.html', data))

    for user in admins:
        send_html_mail_threaded(user, subject, text)

    return


""" Deprecated, has been replaced by `cosinnus.views.map.TileView`! """


class UserListView(EndlessPaginationMixin, ListView):
    model = USER_MODEL
    template_name = 'cosinnus/user/user_list.html'
    items_template = 'cosinnus/user/user_list_items.html'
    paginator_class = Paginator

    def get_queryset(self):
        # get all users from this portal only
        # we also exclude users who have never logged in
        all_users = filter_active_users(
            super(UserListView, self).get_queryset().filter(id__in=CosinnusPortal.get_current().members)
        )

        if self.request.user.is_authenticated:
            visibility_level = BaseTagObject.VISIBILITY_GROUP
        else:
            visibility_level = BaseTagObject.VISIBILITY_ALL

        # only show users with the visibility level
        qs = all_users.filter(cosinnus_profile__media_tag__visibility__gte=visibility_level)
        self.hidden_users = all_users.exclude(cosinnus_profile__media_tag__visibility__gte=visibility_level)

        qs = qs.order_by('first_name', 'last_name')
        qs = qs.select_related('cosinnus_profile')
        return qs

    def get_context_data(self, **kwargs):
        context = super(UserListView, self).get_context_data(**kwargs)
        context.update(
            {
                'hidden_user_count': self.hidden_users.count(),
            }
        )
        return context


user_list = UserListView.as_view()


class UserListMapView(UserListView):
    template_name = 'cosinnus/user/user_list_map.html'


user_list_map = UserListMapView.as_view()


class PortalAdminListView(UserListView):
    template_name = 'cosinnus/user/portal_admin_list.html'

    def get_queryset(self):
        # get all admins from this portal only
        qs = super(UserListView, self).get_queryset()
        qs = qs.exclude(is_active=False).filter(id__in=CosinnusPortal.get_current().admins)
        qs = qs.order_by('first_name', 'last_name')
        qs = qs.select_related('cosinnus_profile')

        self.hidden_users = get_user_model().objects.none()

        return qs


portal_admin_list = PortalAdminListView.as_view()


class SetInitialPasswordMixin:
    """Mixin for set initial password processing."""

    def prepare_initial_profile(self, user):
        """Should be called after the initial password is set."""
        profile = user.cosinnus_profile
        profile_needs_to_saved = False

        try:
            # removing the key from the cosinnus_profile settings to prevent double usage
            profile.settings.pop(PROFILE_SETTING_PASSWORD_NOT_SET)
            profile_needs_to_saved = True
        except KeyError as e:
            logger.error(
                (
                    'Error while deleting key %s from cosinnus_profile settings of user %s. This key is '
                    'supposed to be present. Password was set anyway'
                ),
                extra={'exception': e, 'reason': str(e)},
            )

        # setting your password automatically validates your email, as you have received the mail to your
        # address
        if not profile.email_verified:
            profile.email_verified = True
            profile_needs_to_saved = True

        # add redirect to the welcome-settings page, with priority so that it is shown as first one
        if getattr(settings, 'COSINNUS_SHOW_WELCOME_SETTINGS_PAGE', True):
            profile.add_redirect_on_next_page(
                redirect_with_next(reverse('cosinnus:welcome-settings'), self.request),
                message=None,
                priority=True,
            )
        elif profile_needs_to_saved:
            # if a redirect has been added, the profile has been saved already. otherwise, save it here
            profile.save()

        # send welcome email if enabled
        _send_user_welcome_email_if_enabled(user)


class SetInitialPasswordView(SetInitialPasswordMixin, TemplateView):
    """View that is used to set an initial password for a user, who was created without a initial password.
    Cosinnus.middleware.set_password.SetPasswordMiddleware will redirect every request for a user without an initial
    password to that view.

    :param token: UUID4 token that is send wia mail. Must match user.cosinnus_profile.settings.password_not_set
    """

    template_name = 'cosinnus/registration/password_set_initial_form.html'
    form_class = SetPasswordForm

    def get(self, request, *args, **kwargs):
        token = kwargs['token'] if kwargs.get('token', '') else request.COOKIES.get(PROFILE_SETTING_PASSWORD_NOT_SET)

        if settings.COSINNUS_V3_FRONTEND_ENABLED:
            # in v3 the /set-password/ page handles setting the initial password
            return redirect(f'/set-password/{token}/')

        user = get_user_from_set_password_token(token)

        if user and not request.user.is_authenticated and not user.password:
            form = self.form_class(user=user)
            return render(request, template_name=self.template_name, context={'form': form, 'token': token})
        elif request.user.is_authenticated:
            messages.warning(
                request,
                _(
                    'You are already logged in. This function is only available to set up your account for the first '
                    'time!'
                ),
            )
            raise PermissionDenied()
        else:
            raise Http404

    def post(self, request, *args, **kwargs):
        token = kwargs.get('token', '')
        user = get_user_from_set_password_token(token)

        if user and not request.user.is_authenticated and not user.password:
            form = self.form_class(user=user, data=request.POST)
            if form.is_valid():
                form.save()
                messages.success(
                    self.request,
                    _(
                        'Your password was set successfully! You may now log in using your e-mail address and the '
                        'password you just set.'
                    ),
                )

                # prepare profile
                self.prepare_initial_profile(user)

                # log the user in
                user.backend = 'cosinnus.backends.EmailAuthBackend'
                login(self.request, user)

                # redirect to login page
                # (which will redirect to whatever the portal settings for logged in users are)
                return redirect('login')
            return render(request, template_name=self.template_name, context={'form': form, 'token': token})
        else:
            raise PermissionDenied()


class UserSignupTriggerEventsMixin(object):
    """Mixin for`trigger_events_after_user_signup`,
    used by `UserCreateView` and `SignupView`"""

    message_success = _('Your account "%(user)s" was registered successfully. Welcome to the community!')
    message_success_inactive = _(
        'User "%(user)s" was registered successfully. The account will need to be approved before you can log in. '
        'We will send an email to your address "%(email)s" when this happens.'
    )
    message_success_email_verification = _(
        'Thank you for signing up and welcome to the platform! We sent an email to your address "%(email)s" - please '
        'click the link contained in it to verify your email address!'
    )

    def trigger_events_after_user_signup(self, user, request, request_data=None, skip_messages=False):
        """Triggers all kinds of events and signals after a user has signed up and their profile creation
        has been completed. Should be called after
        `UserSignupFinalizeMixin.finalize_user_object_after_signup`
        @param request_data: if the POST data is not contained in `request.POST`, supply it via this arg
        @param skip_messages: if True, will not trigger any user messages. used when this s
            called via API.
        @return: None or an alternate return redirect URL"""

        # sanity check, retrieve the user's profile (will create it if it doesnt exist)
        if not user.cosinnus_profile:
            get_user_profile_model()._default_manager.get_for_user(user)

        # set current django language during signup as user's profile language
        lang = get_language()
        if not user.cosinnus_profile.language == lang:
            user.cosinnus_profile.language = lang
            user.cosinnus_profile.save(update_fields=['language'])

        # check if there was a token group invite associated with the signup
        request_data = request_data or request.POST
        invite_token = request_data.get('invite_token', None)
        if invite_token:
            invite = get_object_or_None(
                CosinnusGroupInviteToken, token__iexact=invite_token, portal=CosinnusPortal.get_current()
            )
            if not invite:
                messages.warning(
                    request,
                    _(
                        'The invite token you have used does not exist. Please contact the responsible person to get '
                        'a valid link!'
                    ),
                )
            elif not invite.is_active:
                messages.warning(
                    request, _('Sorry, but the invite token you have used is not active yet or not active anymore!')
                )
            else:
                success = apply_group_invite_token_for_user(invite, user)
                if success:
                    messages.success(
                        request, _('Token invitations applied. You are now a member of the associated projects/groups!')
                    )
                else:
                    messages.error(
                        request,
                        _(
                            'There was an error while processing your invites. Some of your invites may not have been '
                            'applied.'
                        ),
                    )
                # also add a welcome-redirect to the first invite group for the user
                # (non-prio so the welcome page shows first!)
                try:
                    first_invite_group = invite.invite_groups.first()
                    user.cosinnus_profile.add_redirect_on_next_page(
                        group_aware_reverse('cosinnus:group-dashboard', kwargs={'group': first_invite_group}),
                        message=None,
                        priority=False,
                    )
                except Exception as e:
                    logger.error(
                        'Error while applying a welcome-redirect from invite token to a freshly signed up user profile',
                        extra={'exception': e, 'reason': str(e)},
                    )

        # set user inactive if this portal needs user approval and send an email to portal admins
        if CosinnusPortal.get_current().users_need_activation:
            user.is_active = False
            user.save()
            data = get_common_mail_context(request)
            data.update(
                {
                    'user': user,
                }
            )
            # message portal admins of request
            subject = render_to_string('cosinnus/mail/user_register_notification_subj.txt', data)
            email_portal_admins(subject, 'cosinnus/mail/user_register_notification.html', data)
            # message user for pending request
            subj_user = render_to_string('cosinnus/mail/user_registration_pending_subj.txt', data)
            text = textfield(render_to_string('cosinnus/mail/user_registration_pending.html', data))
            send_html_mail_threaded(user, subj_user, text)
            if not skip_messages:
                messages.success(request, self.message_success_inactive % {'user': user.email, 'email': user.email})
            # since anonymous users have no session, show the success message in the template via a flag
            return redirect_with_next(reverse('login'), request)
        else:
            # if registrations are open, the user may log in immediately. set the email_verified flag depending
            # on portal settings
            do_login = True
            if CosinnusPortal.get_current().email_needs_verification:
                # send out an instant "please verifiy your e-mail" mail after the user registers,
                # if this is enabled, or the portal locks signups behind verifying the mail
                # if this is not set, users have to manually click the "send verification mail" site header to verify
                if (
                    settings.COSINNUS_USER_SIGNUP_SEND_VERIFICATION_MAIL_INSTANTLY
                    or settings.COSINNUS_USER_SIGNUP_FORCE_EMAIL_VERIFIED_BEFORE_LOGIN
                ):
                    send_user_email_to_verify(user, user.email, request)
                    if not skip_messages:
                        messages.success(request, self.message_success_email_verification % {'email': user.email})
                else:
                    if not skip_messages:
                        messages.success(request, self.message_success % {'user': user.email})
                if settings.COSINNUS_USER_SIGNUP_FORCE_EMAIL_VERIFIED_BEFORE_LOGIN:
                    # show message to tell the user they need to register on this portal
                    if not skip_messages:
                        messages.warning(
                            request,
                            _(
                                'You need to verify your email before logging in. We have just sent you an email with '
                                "a verifcation link. Please check your inbox, and if you haven't received an email, "
                                'please check your spam folder.'
                            ),
                        )
                    do_login = False
            else:
                user_profile = user.cosinnus_profile
                user_profile.email_verified = True
                user_profile.save()
                _send_user_welcome_email_if_enabled(user)
                if not skip_messages:
                    messages.success(request, self.message_success % {'user': user.email})

            if do_login:
                # log the user in
                user.backend = 'cosinnus.backends.EmailAuthBackend'
                login(request, user)

            # send user account creation signal, the audience is empty because this is a moderator-only notification
            user_profile = user.cosinnus_profile
            # need to attach a group to notification objects
            forum_slug = getattr(settings, 'NEWW_FORUM_GROUP_SLUG', None)
            forum_group = get_object_or_None(
                get_cosinnus_group_model(), slug=forum_slug, portal=CosinnusPortal.get_current()
            )
            setattr(user_profile, 'group', forum_group)
            cosinnus_notifications.user_account_created.send(sender=self, user=user, obj=user_profile, audience=[])

        # send user registration signal
        signals.user_registered.send(sender=self, user=user)

        if getattr(settings, 'COSINNUS_SHOW_WELCOME_SETTINGS_PAGE', True):
            # add redirect to the welcome-settings page, with priority so that it is shown as first one
            user.cosinnus_profile.add_redirect_on_next_page(
                redirect_with_next(reverse('cosinnus:welcome-settings'), request), message=None, priority=True
            )
        return None


class UserCreateView(UserSignupTriggerEventsMixin, CreateView):
    form_class = UserCreationForm
    model = USER_MODEL
    template_name = 'cosinnus/registration/signup.html'

    def get_initial(self):
        """Allow pre-populating managed tags on signup using URL params /signup/?mtag=tag1,tag2"""
        initial = super().get_initial()
        # match managed tag param and set it as comma-seperated initial
        if (
            settings.COSINNUS_MANAGED_TAGS_ENABLED
            and settings.COSINNUS_MANAGED_TAGS_USERS_MAY_ASSIGN_SELF
            and settings.COSINNUS_MANAGED_TAGS_IN_SIGNUP_FORM
        ):
            if self.request.GET.get('mtag', None):
                initial['managed_tag_field'] = self.request.GET.get('mtag')
            elif settings.COSINNUS_MANAGED_TAGS_DEFAULT_INITIAL_SLUG is not None:
                initial['managed_tag_field'] = settings.COSINNUS_MANAGED_TAGS_DEFAULT_INITIAL_SLUG
        return initial

    def get_success_url(self):
        return redirect_with_next(reverse('login'), self.request)

    def form_valid(self, form):
        ret = super(UserCreateView, self).form_valid(form)
        user = self.object
        redirect = self.trigger_events_after_user_signup(user, self.request)
        if redirect:
            ret = HttpResponseRedirect(redirect)
        return ret

    def dispatch(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            messages.info(self.request, _('You are already logged in!'))
            return redirect('/')
        if not settings.COSINNUS_USER_SIGNUP_ENABLED:
            messages.error(self.request, _('User signup is currently disabled!'))
            return redirect('/')
        return super(UserCreateView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UserCreateView, self).get_context_data(**kwargs)
        context['submit_label'] = _('Create')
        return context


user_create = check_honeypot(UserCreateView.as_view())


class WelcomeSettingsView(RequireLoggedInMixin, TemplateView):
    """A welcome settings page that saves the two most important privacy aspects:
    the global notification setting and the userprofile visibility setting."""

    template_name = 'cosinnus/user/welcome_settings.html'
    # not showing this message as it is not showing immediately if redirected to dashboard
    # and is confusing
    message_success = None  # _('Your privacy settings were saved. Welcome!')

    def post(self, request, *args, **kwargs):
        self.get_data()
        with transaction.atomic():
            # save language preference:
            notification_setting = request.POST.get('notification_setting', None)
            if notification_setting is not None and int(notification_setting) in (
                choice for choice, label in self.notification_choices
            ):
                self.notification_setting.setting = int(notification_setting)
                # rocketchat: on a global "never", we always set the rocketchat setting to "off"
                if (
                    settings.COSINNUS_ROCKET_ENABLED
                    and self.notification_setting.setting == GlobalUserNotificationSetting.SETTING_NEVER
                ):
                    from cosinnus_message.rocket_chat import RocketChatConnection, RocketChatDownException
                    from cosinnus_message.utils.utils import (
                        save_rocketchat_mail_notification_preference_for_user_setting,  # noqa
                    )

                    self.notification_setting.rocketchat_setting = GlobalUserNotificationSetting.ROCKETCHAT_SETTING_OFF
                    try:
                        save_rocketchat_mail_notification_preference_for_user_setting(
                            self.request.user, self.notification_setting.rocketchat_setting
                        )
                    except RocketChatDownException:
                        logger.error(RocketChatConnection.ROCKET_CHAT_DOWN_ERROR)
                    except Exception as e:
                        logger.exception(e)
                self.notification_setting.save()
            # save visibility setting:
            visibility_setting = request.POST.get('visibility_setting', None)
            if visibility_setting is not None and int(visibility_setting) in (
                choice for choice, label in self.visibility_choices
            ):
                self.media_tag.visibility = int(visibility_setting)
                self.media_tag.save()

        messages.success(request, self.message_success)

        # conference groups
        user_conferences = CosinnusConference.objects.get_for_user(request.user)
        if len(user_conferences) > 0:
            # if the user is part of a conference, redirect there after the welcome screen
            redirect_url = user_conferences[0].get_absolute_url()
        elif getattr(settings, 'COSINNUS_USE_V2_DASHBOARD', False) or (
            getattr(settings, 'COSINNUS_USE_V2_DASHBOARD_ADMIN_ONLY', False) and self.request.user.is_superuser
        ):
            redirect_url = reverse('cosinnus:user-dashboard')
        else:
            redirect_url = (
                get_cosinnus_group_model()
                .objects.get(slug=getattr(settings, 'NEWW_FORUM_GROUP_SLUG'))
                .get_absolute_url()
                if hasattr(settings, 'NEWW_FORUM_GROUP_SLUG')
                else '/'
            )
        redirect_url = redirect_next_or(self.request, redirect_url)
        return HttpResponseRedirect(redirect_url)

    def get_context_data(self, **kwargs):
        context = super(WelcomeSettingsView, self).get_context_data(**kwargs)
        # profile_model = get_user_profile_model()
        self.get_data()
        context.update(
            {
                'visibility_setting': self.media_tag.visibility,
                'visibility_choices': self.visibility_choices,
                'notification_choices': self.notification_choices,
                'notification_setting': self.notification_setting.setting,
            }
        )
        return context

    def get_data(self):
        self.media_tag = self.request.user.cosinnus_profile.media_tag
        self.visibility_choices = self.media_tag.VISIBILITY_CHOICES
        self.notification_setting = GlobalUserNotificationSetting.objects.get_object_for_user(self.request.user)
        # exclude the "individual" option, as this can only be set in notification preferences
        self.notification_choices = [
            choice
            for choice in self.notification_setting.SETTING_CHOICES
            if choice[0] != self.notification_setting.SETTING_GROUP_INDIVIDUAL
        ]


welcome_settings = WelcomeSettingsView.as_view()


class CosinnusGroupInviteTokenEnterView(TemplateView):
    """A welcome settings page that saves the two most important privacy aspects:
    the global notification setting and the userprofile visibility setting."""

    template_name = 'cosinnus/user/group_invite_token_enter.html'

    def post(self, request, *args, **kwargs):
        token = request.POST.get('token', None)
        if not token:
            messages.error(request, _('Please enter a token!'))
            redirect_url = '.'
        else:
            redirect_url = reverse('cosinnus:group-invite-token', kwargs={'token': token})
        return HttpResponseRedirect(redirect_url)


group_invite_token_enter_view = CosinnusGroupInviteTokenEnterView.as_view()


class CosinnusGroupInviteTokenView(TemplateView):
    """A welcome settings page that saves the two most important privacy aspects:
    the global notification setting and the userprofile visibility setting."""

    template_name = 'cosinnus/user/group_invite_token.html'
    message_success = _('Token invitations applied. You are now a member of the associated projects/groups!')

    def dispatch(self, request, *args, **kwargs):
        self.token = kwargs.get('token', None)
        if settings.COSINNUS_V3_FRONTEND_ENABLED:
            # in v3 the /signup/ page handles the invite token
            return redirect(f'/signup/?invite_token={self.token}')
        self.invite = get_object_or_None(
            CosinnusGroupInviteToken, token__iexact=self.token, portal=CosinnusPortal.get_current()
        )
        if not self.token or not self.invite:
            messages.error(
                self.request,
                _(
                    'The invite token you have used does not exist. Please contact the responsible person to get a '
                    'valid link!'
                ),
            )
            return redirect('cosinnus:group-invite-token-enter')
        self.invite_groups = list(self.invite.invite_groups.all())
        return super(CosinnusGroupInviteTokenView, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if self.token and self.invite and self.invite.is_active and self.invite_groups:
            success = apply_group_invite_token_for_user(self.invite, request.user)
            if success:
                redirect_url = self.invite_groups[0].get_absolute_url()
                messages.success(request, self.message_success)
            else:
                redirect_url = '.'
                messages.error(
                    request,
                    _(
                        'There was an error while processing your invites. Some of your invites may not have been '
                        'applied.'
                    ),
                )
            return HttpResponseRedirect(redirect_url)
        else:
            return HttpResponseRedirect('.')

    def get_context_data(self, **kwargs):
        context = super(CosinnusGroupInviteTokenView, self).get_context_data(**kwargs)
        if not self.invite.is_active:
            messages.warning(
                self.request, _('Sorry, but the invite token you have used is not active yet or not active anymore!')
            )
        elif not self.invite_groups:
            messages.warning(self.request, _('Sorry, but the invite token you have used does not seem to be valid!'))
        else:
            context.update(
                {
                    'token': self.token,
                    'invite': self.invite,
                    'invite_groups': self.invite_groups,
                }
            )
        return context


group_invite_token_view = CosinnusGroupInviteTokenView.as_view()


def apply_group_invite_token_for_user(group_invite_token, user):
    """Applies a `CosinnusGroupInviteToken` for a user, making them a member (if not already) of all groups
    determined by the invite token object.
    @return: True if the user became member of all the groups, False if there was an error"""
    success = True
    with transaction.atomic():
        for group in group_invite_token.invite_groups.all():
            try:
                membership = get_object_or_None(CosinnusGroupMembership, group=group, user=user)
                if membership and membership.status not in MEMBER_STATUS:
                    # if the user had a pending invite, convert them to member
                    membership.status = MEMBERSHIP_MEMBER
                    membership.save()
                elif not membership:
                    # make user a member of the group if they hadn't been before
                    CosinnusGroupMembership.objects.create(group=group, user=user, status=MEMBERSHIP_MEMBER)
                # else the user is already in the group
            except Exception as e:
                logger.error(
                    'Error when trying to apply a token group invite',
                    extra={'exception': force_str(e), 'user': user, 'group': group, 'token': group_invite_token.token},
                )
                success = False

    return success


def _check_user_approval_permissions(request, user_id):
    """Permission checks for user approval/denial views"""
    if not request.method == 'GET':
        return HttpResponseNotAllowed(['GET'])

    if not request.user.is_authenticated:
        return redirect_to_not_logged_in(request)
    elif not check_user_superuser(request.user):
        return redirect_to_403(request)
    return None


def _send_user_welcome_email_if_enabled(user, force=False):
    """If welcome email sending is enabled for this portal, send one out to the given user"""

    # if a welcome email text is set in the portal in admin
    portal = CosinnusPortal.get_current()
    if not portal.welcome_email_active and not force:
        return
    # Using __getitem__ as it handles model field translations.
    text = portal['welcome_email_text'].strip() if portal['welcome_email_text'] else ''
    if not force and (not text or not user):
        return

    # render the text as markdown
    text = textfield(render_html_with_variables(user, text))
    subj_user = _('Welcome to %(portal_name)s!') % {'portal_name': portal.name}
    send_html_mail_threaded(user, subj_user, text, topic_instead_of_subject='')


def approve_user(request, user_id):
    """Approves an inactive, registration pending user and sends out an email to let them know"""
    error = _check_user_approval_permissions(request, user_id)
    if error:
        return error

    try:
        user = USER_MODEL.objects.get(id=user_id)
    except USER_MODEL.DoesNotExist:
        messages.error(
            request,
            _('The user account you were looking for does not exist! Their registration was probably already denied.'),
        )
        return redirect(reverse('cosinnus:profile-detail'))

    if user.is_active:
        messages.success(request, _('The user account was already approved, but thank you anyway!'))
        return redirect(reverse('cosinnus:profile-detail', kwargs={'username': user.username}) + '?force_show=1')

    user.is_active = True
    user.save()

    # message user for accepeted request
    data = get_common_mail_context(request)
    data.update(
        {
            'user': user,
        }
    )
    subj_user = render_to_string('cosinnus/mail/user_registration_approved_subj.txt', data)
    text = textfield(render_to_string('cosinnus/mail/user_registration_approved.html', data))
    send_html_mail_threaded(user, subj_user, text)

    # send user account creation signal, the audience is empty because this is a moderator-only notification
    user_profile = user.cosinnus_profile
    # need to attach a group to notification objects
    forum_slug = getattr(settings, 'NEWW_FORUM_GROUP_SLUG', None)
    forum_group = get_object_or_None(get_cosinnus_group_model(), slug=forum_slug, portal=CosinnusPortal.get_current())
    setattr(user_profile, 'group', forum_group)
    cosinnus_notifications.user_account_created.send(sender=user, user=user, obj=user_profile, audience=[])

    # also send out a verification email if portals have email verification turned on
    if CosinnusPortal.get_current().email_needs_verification:
        send_user_email_to_verify(user, user.email, request)
    else:
        # send the welcome email if no email verification is needed, otherwise the welcome email is sent after the
        # email is verified.
        _send_user_welcome_email_if_enabled(user)

    messages.success(
        request,
        _(
            'Thank you for approving user %(username)s (%(email)s)! An introduction-email was sent out to them and '
            'they can now log in to the site.'
        )
        % {'username': full_name_force(user), 'email': user.email},
    )
    return redirect(reverse('cosinnus:profile-detail', kwargs={'username': user.username}) + '?force_show=1')


def deny_user(request, user_id):
    """Deny a registration pending user. Sends out an email letting them know, then deletes the pending user account.
    Cannot be done for users that are active."""
    error = _check_user_approval_permissions(request, user_id)
    if error:
        return error

    try:
        user = USER_MODEL.objects.get(id=user_id)
    except USER_MODEL.DoesNotExist:
        messages.error(
            request,
            _('The user account you were looking for does not exist! Their registration was probably already denied.'),
        )
        return redirect(reverse('cosinnus:profile-detail'))

    if user.is_active:
        messages.warning(
            request,
            _(
                'The user account %(username)s (%(email)s) was already approved, so you cannot deny the registration! '
                'If this is a problem, you may want to deactivate the user manually from the admin interface.'
            )
            % {'username': full_name_force(user), 'email': user.email},
        )
        return redirect(reverse('cosinnus:profile-detail', kwargs={'username': user.username}) + '?force_show=1')

    # message user for denied request
    admins = get_user_model().objects.filter(id__in=CosinnusPortal.get_current().admins)
    data = get_common_mail_context(request)
    data.update(
        {
            'user': user,
            'admins': admins,
        }
    )
    subj_user = render_to_string('cosinnus/mail/user_registration_denied_subj.txt', data)
    text = textfield(render_to_string('cosinnus/mail/user_registration_denied.html', data))
    send_html_mail_threaded(user, subj_user, text)

    messages.success(
        request,
        _('You have denied the join request of %(username)s (%(email)s)! An email was sent to let them know.')
        % {'username': full_name_force(user), 'email': user.email},
    )
    user.delete()
    return redirect(reverse('cosinnus:profile-detail'))


def verifiy_user_email(request, email_verification_param):
    """
    Verify an email by comparing a token sent only to this email with the one saved in the user profile during
    registration (or email change)
    """
    redirect_url = reverse('cosinnus:profile-detail')
    user_id, token = email_verification_param.split('-', 1)

    try:
        user_id
        user = USER_MODEL.objects.get(id=user_id)
    except (
        USER_MODEL.DoesNotExist,
        ValueError,
    ):
        messages.error(
            request,
            _(
                'The user account you were looking for does not exist! Your registration was probably already denied '
                'or the email token has expired.'
            ),
        )
        return redirect(redirect_url)

    profile = user.cosinnus_profile
    user_was_verified_before = profile.email_verified
    target_email = profile.settings.get(PROFILE_SETTING_EMAIL_TO_VERIFY, None)
    target_token = profile.settings.get(PROFILE_SETTING_EMAIL_VERFICIATION_TOKEN, None)

    if request.user.is_authenticated and request.user.id != user.id:
        messages.error(
            request,
            _(
                'The email you are trying to verify belongs to a different user account than the one you are logged in '
                'with! Please log out before clicking the verification link again!'
            ),
        )
        if user_was_verified_before:
            redirect_url = reverse('cosinnus:user-change-email-pending') + '?error=1'
        return redirect(redirect_url)

    if not target_email or not target_token:
        messages.error(request, _('The email for this account seems to already have been confirmed!'))
        if user_was_verified_before:
            redirect_url = reverse('cosinnus:user-change-email-pending') + '?error=1'
        return redirect(redirect_url)

    if not token == target_token:
        messages.error(request, _('The link you supplied for the email confirmation is no longer valid!'))
        if user_was_verified_before:
            redirect_url = reverse('cosinnus:user-change-email-pending') + '?error=1'
        return redirect(redirect_url)

    # check if target email doesn't already exist in another user instance:
    if target_email and get_user_model().objects.exclude(id=user_id).filter(email__iexact=target_email).count():
        # duplicate email is bad
        messages.error(
            request, _('The email you are trying to confirm has already been confirmed or belongs to another user!')
        )
        return redirect(redirect_url)

    # everything seems to be in order, swap the old with the real email
    with transaction.atomic():
        user.email = target_email
        user.save()
        del profile.settings[PROFILE_SETTING_EMAIL_TO_VERIFY]
        del profile.settings[PROFILE_SETTING_EMAIL_VERFICIATION_TOKEN]
        profile.email_verified = True
        if user_was_verified_before:
            # logout user sessions after email change
            keep_session = request.session if user.is_authenticated else None
            profile.force_logout_user(keep_session=keep_session, save=False)
        profile.save()

    if user.is_active:
        messages.success(request, _('Your email address %(email)s was successfully confirmed!') % {'email': user.email})
        if user_was_verified_before:
            # after an email change, redirect the user to the success page for email changes
            redirect_url = reverse('cosinnus:user-change-email-pending') + '?success=1'
        else:
            # else, welcome the user
            _send_user_welcome_email_if_enabled(user)
        if not request.user.is_authenticated and settings.COSINNUS_USER_SIGNUP_FORCE_EMAIL_VERIFIED_BEFORE_LOGIN:
            # if the v3 frontend is enabled, as a temporary solution do not log in the user directly, but redirect to
            # the verified page instead
            if settings.COSINNUS_V3_FRONTEND_ENABLED:
                return redirect(settings.COSINNUS_V3_FRONTEND_SIGNUP_VERIFICATION_WELCOME_PAGE)
            # log the user in for portals that require a verification first
            user.backend = 'cosinnus.backends.EmailAuthBackend'
            login(request, user)
        return redirect(redirect_url)
    else:
        messages.success(
            request,
            _(
                'Your email address %(email)s was successfully confirmed! However, you account is not active yet and '
                'will have to be approved by an administrator before you can log in. We will send you an email as soon '
                'as that happens!'
            )
            % {'email': user.email},
        )
        return redirect(redirect_url)


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
        return reverse('cosinnus:profile-detail', kwargs={'username': self.object.username})


user_update = UserUpdateView.as_view()


class CosinnusPasswordChangeView(PasswordChangeView):
    """Overridden view that sends a password changed signal"""

    form_class = ValidatedPasswordChangeForm

    def form_valid(self, form):
        ret = super().form_valid(form)
        # send a password changed signal
        signals.user_password_changed.send(sender=self, user=self.request.user)
        return ret


def password_change_proxy(request, *args, **kwargs):
    """Proxies the django.contrib.auth view. Only lets a user see the form or POST to it
    if the user is not a member of an integrated portal."""
    user = request.user
    if user.is_authenticated and check_user_integrated_portal_member(user):
        return TemplateResponse(request, 'cosinnus/registration/password_cannot_be_changed_page.html')
    return CosinnusPasswordChangeView.as_view(*args, **kwargs)(request)


class CosinnusPasswordResetConfirmView(PasswordResetConfirmView):
    """Overridden view that verifies a user's email on successful password reset"""

    def form_valid(self, form):
        ret = super().form_valid(form)
        profile = self.user.cosinnus_profile
        # setting your password automatically validates your email, as you have received the mail to your address
        if not profile.email_verified:
            profile.email_verified = True
            profile.save()
        # send a password changed signal
        signals.user_password_changed.send(sender=self, user=self.user)
        return ret


# =============== set a password from a only by token logged in user =========================== #


class CosinnusSetInitialPasswordView(PasswordResetConfirmView):
    """Overridden view that sends a password changed signal"""

    def form_valid(self, form):
        ret = super().form_valid(form)
        # send a password changed signal
        signals.user_password_changed.send(sender=self, user=self.request.user)
        _send_user_welcome_email_if_enabled(self.request.user)
        return ret


def password_set_initial_proxy(request, *args, **kwargs):
    user = request.user
    if user.is_authenticated and check_user_integrated_portal_member(user):
        return TemplateResponse(request, 'cosinnus/registration/password_cannot_be_changed_page.html')
    return CosinnusSetInitialPasswordView.as_view(*args, **kwargs)(request)


# ================================================================================================= #


class CosinnusPasswordResetForm(PasswordResetForm):
    def send_mail(
        self, subject_template_name, email_template_name, context, from_email, to_email, html_email_template_name=None
    ):
        """
        Sends the email using the Cosinnus mailer instead of the default django one.
        """
        template = email_template_name
        is_html = False
        if html_email_template_name:
            is_html = True
            template = html_email_template_name
        # Email subject *must not* contain newlines
        subject = loader.render_to_string(subject_template_name, context)
        subject = ''.join(subject.splitlines())

        send_mail_or_fail_threaded(to_email, subject, template, context, from_email=from_email, is_html=is_html)


def password_reset_proxy(request, *args, **kwargs):
    """Proxies the django.contrib.auth view. Only send a password reset mail
    if the email doesn't belong to a user that is a member of an integrated portal."""
    if request.method == 'POST':
        email = request.POST.get('email', None)
        user = None
        if email:
            try:
                user = USER_MODEL.objects.get(email__iexact=email, is_active=True)
            except USER_MODEL.DoesNotExist:
                pass
        if user and not check_user_verified(user) and GlobalBlacklistedEmail.is_email_blacklisted(email):
            return TemplateResponse(request, 'cosinnus/registration/password_cannot_be_reset_blacklisted_page.html')
        # disallow integrated users to reset their password
        if user and (user.is_guest or check_user_integrated_portal_member(user)):
            return TemplateResponse(request, 'cosinnus/registration/password_cannot_be_reset_page.html')
        # silently disallow imported/created users without a password to reset their password
        # if the user import functionality is enabled, because then imported users are not active
        # until they have been sent a token invite and may not use the password reset function,
        # *if* they have not yet received a token invite
        if user and not user.password:
            if (
                settings.COSINNUS_USER_IMPORT_ADMINISTRATION_VIEWS_ENABLED
                and settings.COSINNUS_PLATFORM_ADMIN_CAN_EDIT_PROFILES
                and PROFILE_SETTING_LOGIN_TOKEN_SENT not in user.cosinnus_profile.settings
            ):
                return redirect(PasswordResetView().get_success_url())

    kwargs.update(
        {
            'form_class': CosinnusPasswordResetForm,
        }
    )
    return PasswordResetView.as_view(*args, **kwargs)(request)


def send_user_email_to_verify(user, new_email, request=None, user_has_just_registered=True):
    """Sets the profile variables for a user to confirm a pending email,
    and sends out an email with a verification URL to the user.
    @param user_has_just_registered: If this True, a welcome email will be sent.
        If False, an email change email will be sent."""

    new_email = new_email.strip().lower()
    # the verification param for the URL consists of <user-id>-<uuid>, where the uuid is saved to the user's profile
    a_uuid = uuid1()
    verification_url_param = '%d-%s' % (user.id, a_uuid)
    user.cosinnus_profile.settings[PROFILE_SETTING_EMAIL_TO_VERIFY] = new_email
    user.cosinnus_profile.settings[PROFILE_SETTING_EMAIL_VERFICIATION_TOKEN] = a_uuid
    user.cosinnus_profile.save()

    # message user for email verification
    if request:
        # create a readonly temp copy of the user object with the new email
        # so we can send the mail to the new e-mail address
        def _protected_func(*args, **kwargs):
            raise ImproperlyConfigured('This function cannot be used on a User instance converted to readonly!')

        readonly_temp_user = copy(user)
        setattr(readonly_temp_user, 'save', _protected_func)  # replace writing functions
        setattr(readonly_temp_user, 'delete', _protected_func)  # replace writing functions
        readonly_temp_user.email = new_email

        data = get_common_mail_context(request)
        user_verification_url = (
            CosinnusPortal.get_current().get_domain()
            + reverse('cosinnus:user-verifiy-email', kwargs={'email_verification_param': verification_url_param})
            + redirect_with_next('', request)
        )
        data.update(
            {
                'site_name': settings.COSINNUS_BASE_PAGE_TITLE_TRANS,
                'user': readonly_temp_user,
                'user_email': readonly_temp_user.email,
                'user_verification_url': user_verification_url,
            }
        )
        subject = _('Please verify your email address for %(site_name)s!') % data

        if user_has_just_registered:
            text = (
                str(_("You have just registered an account at %(site_name)s. We're happy to see you!") % data) + '\n\n'
            )
        else:
            text = str(_('You have just changed your email address at %(site_name)s.') % data) + '\n\n'
        text += (
            str(
                _(
                    'Please verify your email address by clicking on the following link (or copy and paste the link it '
                    'in your browser):'
                )
                % data
            )
            + '\n\n'
        )
        text += user_verification_url + '\n\n'
        text += str(_('Thank you!') % data) + '\n\n'
        text += str(_('Your %(site_name)s Team') % data) + '\n\n'
        text += '---\n\n'
        text += (
            str(
                _(
                    'If you did not sign up for an account you may ignore this email. You can also click the '
                    'unsubscrible link on the bottom of this email to never receive mails from us again!'
                )
                % data
            )
            + '\n\n'
        )

        # send a notification email ignoring notification settings
        if not GlobalBlacklistedEmail.is_email_blacklisted(readonly_temp_user.email):
            body_text = textfield(text)
            send_html_mail_threaded(readonly_temp_user, subject, body_text)


def email_first_login_token_to_user(user, threaded=True):
    """Sets the profile variables for a user to login without a set password,
    and sends out an email with a verification URL to the user.
    """

    # the verification param for the URL consists of <user-id>-<uuid>, where the uuid is saved to the user's profile
    a_uuid = uuid4()
    user.cosinnus_profile.settings[PROFILE_SETTING_PASSWORD_NOT_SET] = str(a_uuid)
    user.cosinnus_profile.save()

    # message user for email verification
    data = get_common_mail_context(None)
    data.update(
        {
            'user': user,
            'user_email': user.email,
            'verification_token': reverse('password_set_initial', kwargs={'token': str(a_uuid)}),
        }
    )
    template = 'cosinnus/mail/user_email_first_token.html'

    data.update(
        {
            'content': render_to_string(template, data),
        }
    )
    subj_user = render_to_string('cosinnus/mail/user_email_first_token_subj.txt', data)

    if threaded:
        send_mail_func = send_mail_or_fail_threaded
    else:
        send_mail_func = send_mail_or_fail
    send_mail_func(user.email, subj_user, None, data)

    user.cosinnus_profile.settings[PROFILE_SETTING_LOGIN_TOKEN_SENT] = timezone.now()
    user.cosinnus_profile.save()


def user_api_me(request):
    """Returns a JSON dict of publicly available user data about the currently logged-in user.
    Returens {} if no user is logged in this session."""
    data = {}
    if request.user.is_authenticated:
        user = request.user
        user_societies = CosinnusSociety.objects.get_for_user(request.user)
        user_projects = CosinnusProject.objects.get_for_user(request.user)

        # euro amount if current subscription payments for this user
        is_paying = 0
        if getattr(settings, 'COSINNUS_PAYMENTS_ENABLED', False):
            from wechange_payments.models import Subscription

            current_subscription = Subscription.get_current_for_user(request.user)
            if current_subscription:
                is_paying = int(current_subscription.amount)

        data.update(
            {
                'username': user.username,
                'id': user.id,
                'first_name': user.first_name or '',
                'last_name': user.last_name or '',
                'avatar_url': CosinnusPortal.get_current().get_domain()
                + user.cosinnus_profile.get_avatar_thumbnail_url(),
                'groups': [society.slug for society in user_societies],
                'projects': [project.slug for project in user_projects],
                'is_paying': is_paying,
            }
        )

    return JsonResponse(data)


def add_email_to_blacklist(request, email, token):
    """Adds an email to the email blacklist. Used for generating list-unsubscribe links in our emails.
    Use `email_blacklist_token_generator.make_token(email)` to generate a token."""

    if not is_email_valid(email):
        messages.error(request, _('The unsubscribe link you have clicked does not seem to be valid!') + ' (1)')
        return redirect('cosinnus:user-add-email-blacklist-result')

    if not email_blacklist_token_generator.check_token(email, token):
        messages.error(request, _('The unsubscribe link you have clicked does not seem to be valid!') + ' (2)')
        return redirect('cosinnus:user-add-email-blacklist-result')

    logger.warn(
        'Adding email to blacklist from URL link', extra={'email': email, 'portal': CosinnusPortal.get_current().id}
    )

    GlobalBlacklistedEmail.add_for_email(email)

    messages.success(
        request,
        _(
            'We have unsubscribed your email "%(email)s" from our mailing list. You will not receive any more emails '
            'from us!'
        )
        % {'email': email},
    )
    return redirect('cosinnus:user-add-email-blacklist-result')


def add_email_to_blacklist_result(request):
    """We redirect to a different URL because the original URL is valid forever,
    and the browser tab may get reloaded and we don't want to fire another
    unsubscribe each time.
    It is expected that there is a messages.success or error message queued when arriving here"""
    return render(request, 'cosinnus/common/200.html')


def accept_tos(request):
    """A bare-bones ajax endpoint to save that a user has accepted the ToS settings.
    The frontend doesn't care about a return values, so we don't either
    (on fail, the user will just see another popup on next request)."""
    if not request.method == 'POST':
        return HttpResponseNotAllowed(['POST'])
    if not request.user.is_authenticated:
        return HttpResponseForbidden('You must be logged in to do that!')
    try:
        accept_user_tos_for_portal(request.user)
    except Exception as e:
        logger.error('Error in `user.accept_tos`: %s' % e, extra={'exception': e})
    return JsonResponse({'status': 'ok'})


def resend_email_validation(request):
    if request.method != 'GET':
        return HttpResponseNotAllowed('GET')
    if not request.user.is_authenticated:
        return HttpResponseForbidden('Must be logged in!')
    if not GlobalBlacklistedEmail.is_email_blacklisted(request.user.email):
        send_user_email_to_verify(request.user, request.user.email, request)
        messages.add_message(request, messages.SUCCESS, _('A new verification email has been sent.'))
    return HttpResponseRedirect(redirect_next_or(request, reverse('cosinnus:profile-detail')))


def accept_updated_tos(request):
    """A bare-bones ajax endpoint to save a user's accepted ToS settings and newsletter settings.
    The frontend doesn't care about a return values, so we don't either
    (on fail, the user will just see another popup on next request)."""
    if request.method != 'POST':
        return HttpResponseNotAllowed('POST')
    if not request.user.is_authenticated:
        return HttpResponseForbidden('Must be logged in!')
    cosinnus_profile = request.user.cosinnus_profile

    form = TermsOfServiceFormFields(request.POST)
    if form.is_valid():
        # set the newsletter opt-in
        if settings.COSINNUS_USERPROFILE_ENABLE_NEWSLETTER_OPT_IN:
            cosinnus_profile.settings['newsletter_opt_in'] = form.cleaned_data.get('newsletter_opt_in')
        # set the user's tos_accepted flag to true and date to now
        accept_user_tos_for_portal(request.user, profile=cosinnus_profile, save=True)
        return HttpResponse('Ok')
    else:
        logger.warning(
            "Could not save a user's updated ToS settings.", extra={'errors': form.errors, 'post-data': request.POST}
        )
        return HttpResponseServerError('Failed')


class UserSelect2View(Select2View):
    """
    This view is used as API backend to serve the suggestions for the message recipient field.
    """

    HARD_USER_LIMIT = 50

    def check_all_permissions(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated:
            raise PermissionDenied

    def get_results(self, request, term, page, context):
        terms = term.strip().lower().split(' ')
        q = get_user_query_filter_for_search_terms(terms)

        users = get_user_model().objects.filter(q).exclude(id__exact=request.user.id)
        users = filter_active_users(users)
        # hard limit user count that we search for so we don't die on very short fuzzy searches,
        # and do this before the expensive visibility checks
        users = users[: self.HARD_USER_LIMIT]
        # as a last filter, remove all users that that have their privacy setting to "only members of groups i am in",
        # if they aren't in a group with the user
        users = [user for user in users if check_user_can_see_user(request.user, user)]

        # check for a direct email match for users to always find a user like that
        direct_email_user = get_user_by_email_safe(term)
        if direct_email_user and check_user_can_see_user(request.user, direct_email_user):
            users.append(direct_email_user)

        # Filter all groups the user is a member of. No longer allows messaging public groups
        #   that the user is not a member of.
        # The Forum can never be messaged unless the user is an admin.
        # Use CosinnusGroup.objects.get_cached() to search in all groups instead
        groups = list(get_cosinnus_group_model().objects.get_for_user(request.user))
        forum_slug = getattr(settings, 'NEWW_FORUM_GROUP_SLUG', None)
        groups = [
            group
            for group in groups
            if all([term.lower() in group.name.lower() for term in terms])
            and (check_user_superuser(request.user) or group.slug != forum_slug)
        ]

        # these result sets are what select2 uses to build the choice list
        # results = [
        #   ("user:" + six.text_type(user.id), render_to_string(
        #       'cosinnus/common/user_select_pill.html',
        #       {'type':'user','text':escape(user.first_name) + " " + escape(user.last_name), 'user': user}),)
        #   for user in users]
        # results.extend(
        #   [("group:" + six.text_type(group.id),
        #       render_to_string('cosinnus/common/user_select_pill.html', {'type':'group','text':escape(group.name)}),)
        #   for group in groups])

        # sort results
        users = sorted(users, key=lambda useritem: full_name(useritem).lower())
        groups = sorted(groups, key=lambda groupitem: groupitem.name.lower())

        results = get_user_select2_pills(users)
        results.extend(get_group_select2_pills(groups))

        # Any error response, Has more results, options list
        return (NO_ERR_RESP, False, results)


class UserChangeEmailView(RequireLoggedInMixin, FormView):
    """A view that lets the user change their email and guides them through the validation"""

    form_class = UserChangeEmailFormWithPasswordValidation
    template_name = 'cosinnus/user/user_change_email_form.html'

    def get_success_url(self):
        return reverse('cosinnus:user-change-email-pending')

    def form_valid(self, form):
        ret = super(UserChangeEmailView, self).form_valid(form)
        new_email = form.cleaned_data.get('email')
        # send out email-change-verification mail
        send_user_email_to_verify(self.request.user, new_email, self.request, user_has_just_registered=False)

        return ret

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update({})
        return context


change_email_view = UserChangeEmailView.as_view()


class UserChangeEmailPendingView(RequireLoggedInMixin, TemplateView):
    """Pending and confirm pages for `UserChangeEmailView`."""

    template_name = 'cosinnus/user/user_change_email_pending.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(
            {'pending_email': self.request.user.cosinnus_profile.settings.get(PROFILE_SETTING_EMAIL_TO_VERIFY, None)}
        )
        return context


change_email_pending_view = UserChangeEmailPendingView.as_view()


class GuestUserSignupView(FormView):
    """Guest access for a given `UserGroupGuestAccess` token."""

    form_class = UserGroupGuestAccessForm
    template_name = 'cosinnus/user/guest_user_signup.html'
    guest_access = None
    group = None

    msg_invalid_token = _('Invalid guest token.')
    msg_already_logged_in = _(
        'You are currently logged in. The guest access can only be used if you are not logged in.'
    )
    msg_signup_not_possible = _('We could not sign you in as a guest at this time. Please try again later!')

    def dispatch(self, request, *args, **kwargs):
        # check if feature is disabled on this portal
        if not settings.COSINNUS_USER_GUEST_ACCOUNTS_ENABLED:
            raise Http404
        # check if guest token and its access object and group exists
        guest_token_str = kwargs.pop('guest_token', '').strip().lower()
        if guest_token_str:
            self.guest_access = get_object_or_None(UserGroupGuestAccess, token__iexact=guest_token_str)
        if self.guest_access:
            self.group = self.guest_access.group
        if not self.group or not self.group.is_active:
            # do not allow to tokens without a group or an inactive group
            messages.warning(request, self.msg_invalid_token)
            return redirect_to_error_page(request, view=self)
        # check if feature is disabled on this portal for this group type
        if self.group.type not in settings.COSINNUS_USER_GUEST_ACCOUNTS_FOR_GROUP_TYPE:
            raise Http404
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        # show warning for logged in users
        if request.user.is_authenticated:
            messages.warning(request, self.msg_already_logged_in)
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # disallow for logged in users
        if request.user.is_authenticated:
            messages.warning(request, self.msg_already_logged_in)
            return redirect_to_error_page(request, view=self)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        username = form.cleaned_data['username']
        success = create_guest_user_and_login(self.guest_access, username, self.request)
        # if not successful, render to form and show error
        if not success:
            messages.error(self.request, self.msg_signup_not_possible)
            return self.render_to_response(self.get_context_data(form=form))
        return redirect('cosinnus:user-dashboard')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'guest_group': self.group,
            }
        )
        # remove form if user is logged in so they only see the error message
        if self.request.user.is_authenticated and 'form' in context:
            del context['form']
        return context


guest_user_signup_view = GuestUserSignupView.as_view()


class GuestUserNotAllowedView(TemplateView):
    template_name = 'cosinnus/user/guest_user_not_allowed.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.is_guest:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


guest_user_not_allowed_view = GuestUserNotAllowedView.as_view()


@receiver(userprofile_created)
def convert_email_group_invites(sender, profile, **kwargs):
    """Converts all `CosinnusUnregisterdUserGroupInvite` to `CosinnusGroupMembership` pending invites
    for a user after registration. If there were any, also adds an entry to the user's profile's visit-next setting."""
    # TODO: caching?
    user = profile.user
    invites = CosinnusUnregisterdUserGroupInvite.objects.filter(email__iexact=get_newly_registered_user_email(user))
    if invites:
        with transaction.atomic():
            other_invites = []
            for invite in invites:
                # skip inviting to auto-invite groups, users are in them automatically
                if invite.group.slug in get_default_user_group_slugs():
                    continue
                # check if the inviting user may invite directly
                if invite.invited_by_id in invite.group.admins:
                    CosinnusGroupMembership.objects.get_or_create(
                        group=invite.group,
                        user=user,
                        defaults={
                            'status': MEMBERSHIP_INVITED_PENDING,
                        },
                    )
                else:
                    other_invites.append(invite.group.id)
            # trigger translation indexing
            _(
                'Welcome! You were invited to the following projects and groups. Please click the dropdown button to '
                'accept or decline the invitation for each of them!'
            )
            msg = (
                'Welcome! You were invited to the following projects and groups. Please click the dropdown button to '
                'accept or decline the invitation for each of them!'
            )
            # create a user-settings-entry
            if other_invites:
                profile.settings['group_recruits'] = other_invites
            profile.add_redirect_on_next_page(reverse('cosinnus:invitations'), msg)
            # we actually do not delete the invites here yet, for many reasons such as re-registers when email
            # verification didn't work the invites will be deleted upon first login using the
            # `user_logged_in_first_time` signal


@receiver(userprofile_created)
def remove_user_from_blacklist(sender, profile, **kwargs):
    user = profile.user
    email = get_newly_registered_user_email(user)
    GlobalBlacklistedEmail.remove_for_email(email)


@receiver(userprofile_created)
def create_user_notification_setting(sender, profile, **kwargs):
    user = profile.user
    GlobalUserNotificationSetting.objects.get_object_for_user(user)


@receiver(user_logged_in)
def detect_first_user_login(sender, user, request, **kwargs):
    """Used to send out the user_first_logged_in_first_time signal"""
    profile = user.cosinnus_profile
    first_login = profile.settings.get(PROFILE_SETTING_FIRST_LOGIN, None)
    if not first_login:
        profile.settings[PROFILE_SETTING_FIRST_LOGIN] = force_str(user.last_login)
        profile.save(update_fields=['settings'])
        user_logged_in_first_time.send(sender=sender, user=user, request=request)


@receiver(user_logged_in_first_time)
def cleanup_user_after_first_login(sender, user, request, **kwargs):
    """Cleans up pre-registration objects and settings"""
    CosinnusUnregisterdUserGroupInvite.objects.filter(email=user.email).delete()
