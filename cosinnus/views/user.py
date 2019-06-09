# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
from django.contrib.auth import get_user_model, login as auth_login, logout as auth_logout,\
    login
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm
from django.urls import reverse, reverse_lazy
from django.db import transaction
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _, get_language
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from cosinnus.core.decorators.views import staff_required, superuser_required,\
    redirect_to_not_logged_in, redirect_to_403
from cosinnus.forms.user import UserCreationForm, UserChangeForm,\
    TermsOfServiceFormFields
from cosinnus.views.mixins.ajax import patch_body_json_data
from cosinnus.utils.http import JSONResponse
from django.contrib import messages
from cosinnus.models.profile import get_user_profile_model,\
    PROFILE_SETTING_EMAIL_TO_VERIFY, PROFILE_SETTING_EMAIL_VERFICIATION_TOKEN,\
    PROFILE_SETTING_FIRST_LOGIN, GlobalBlacklistedEmail,\
    GlobalUserNotificationSetting
from cosinnus.models.tagged import BaseTagObject
from cosinnus.models.group import CosinnusPortal,\
    CosinnusUnregisterdUserGroupInvite, CosinnusGroupMembership,\
    MEMBERSHIP_INVITED_PENDING, CosinnusGroupInviteToken, MEMBERSHIP_MEMBER,\
    MEMBER_STATUS
from cosinnus.core.mail import MailThread, get_common_mail_context,\
    send_mail_or_fail_threaded
from django.template.loader import render_to_string
from django.http.response import HttpResponseNotAllowed, JsonResponse, HttpResponseRedirect,\
    HttpResponseForbidden, HttpResponse, HttpResponseServerError
from django.shortcuts import redirect, render
from cosinnus.templatetags.cosinnus_tags import full_name_force
from cosinnus.utils.permissions import check_user_integrated_portal_member
from django.template.response import TemplateResponse
from django.core.paginator import Paginator
from cosinnus.views.mixins.group import EndlessPaginationMixin,\
    RequireLoggedInMixin
from cosinnus.utils.user import filter_active_users,\
    get_newly_registered_user_email
from uuid import uuid1
from django.utils.encoding import force_text
from cosinnus.core import signals
from django.dispatch.dispatcher import receiver
from cosinnus.core.signals import userprofile_ceated, user_logged_in_first_time
from django.contrib.auth.signals import user_logged_in
from cosinnus.conf import settings
from cosinnus.utils.tokens import email_blacklist_token_generator
from cosinnus.utils.functions import is_email_valid
from django.views.generic.base import TemplateView
from cosinnus.utils.urls import redirect_with_next, redirect_next_or
from cosinnus.utils.group import get_cosinnus_group_model
from django.template import loader

from honeypot.decorators import check_honeypot
from annoying.functions import get_object_or_None

import logging
from django.contrib.auth.views import PasswordChangeView, PasswordResetView
from django.utils.timezone import now
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
logger = logging.getLogger('cosinnus')

USER_MODEL = get_user_model()


def email_portal_admins(subject, template, data):
    mail_thread = MailThread()
    admins = get_user_model().objects.filter(id__in=CosinnusPortal.get_current().admins)
    
    for user in admins:
        mail_thread.add_mail(user.email, subject, template, data)
    mail_thread.start()


""" Deprecated, has been replaced by `cosinnus.views.map.TileView`! """
class UserListView(EndlessPaginationMixin, ListView):

    model = USER_MODEL
    template_name = 'cosinnus/user/user_list.html'
    items_template = 'cosinnus/user/user_list_items.html'
    paginator_class = Paginator
    
    def get_queryset(self):
        
        # get all users from this portal only        
        # we also exclude users who have never logged in
        all_users = filter_active_users(super(UserListView, self).get_queryset().filter(id__in=CosinnusPortal.get_current().members))
        
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
        context.update({
            'hidden_user_count': self.hidden_users.count(),
        })
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
        qs = qs.exclude(is_active=False).\
                        filter(id__in=CosinnusPortal.get_current().admins)
        qs = qs.order_by('first_name', 'last_name')
        qs = qs.select_related('cosinnus_profile')
        
        self.hidden_users = get_user_model().objects.none()
        
        return qs
    
portal_admin_list = PortalAdminListView.as_view()



class UserCreateView(CreateView):

    form_class = UserCreationForm
    model = USER_MODEL
    template_name = 'cosinnus/registration/signup.html'

    message_success = _('Your account "%(user)s" was registered successfully. Welcome to the community!')
    message_success_inactive = _('User "%(user)s" was registered successfully. The account will need to be approved before you can log in. We will send an email to your address "%(email)s" when this happens.')
    message_success_email_verification = _('User "%(user)s" was registered successfully. We will send an email to your address %(email)s" soon. You need to confirm the email address before you can log in.')
    
    def get_success_url(self):
        return redirect_with_next(reverse('login'), self.request)
    
    def form_valid(self, form):
        ret = super(UserCreateView, self).form_valid(form)
        user = self.object
        
        # sanity check, retrieve the user's profile (will create it if it doesnt exist)
        profile = user.cosinnus_profile or get_user_profile_model()._default_manager.get_for_user(user)
        
        # set current django language during signup as user's profile language
        lang = get_language()
        if not profile.language == lang:
            profile.language = lang
            profile.save(update_fields=['language']) 
        
        # set user inactive if this portal needs user approval and send an email to portal admins
        if CosinnusPortal.get_current().users_need_activation:
            user.is_active = False
            user.save()
            data = get_common_mail_context(self.request)
            data.update({
                'user': user,
            })
            # message portal admins of request
            subject = render_to_string('cosinnus/mail/user_register_notification_subj.txt', data)
            email_portal_admins(subject, 'cosinnus/mail/user_register_notification.html', data)
            # message user for pending request
            subj_user = render_to_string('cosinnus/mail/user_registration_pending_subj.txt', data)
            send_mail_or_fail_threaded(user.email, subj_user, 'cosinnus/mail/user_registration_pending.html', data)
            
            messages.success(self.request, self.message_success_inactive % {'user': user.email, 'email': user.email})
        
        # scramble this users email so he cannot log in until he verifies his email, if the portal has this enabled
        if CosinnusPortal.get_current().email_needs_verification:
            
            with transaction.atomic():
                # scramble actual email so the user cant log in but can be found in the admin
                original_user_email = user.email  # don't show the scrambled emai later on
                user.email = '__unverified__%s__%s' % (str(uuid1())[:8], original_user_email)
                user.save()
                set_user_email_to_verify(user, original_user_email, self.request)
            
            messages.success(self.request, self.message_success_email_verification % {'user': original_user_email, 'email': original_user_email})

        if not CosinnusPortal.get_current().users_need_activation and not CosinnusPortal.get_current().email_needs_verification:
            messages.success(self.request, self.message_success % {'user': user.email})
            user.backend = 'cosinnus.backends.EmailAuthBackend'
            login(self.request, user)
        
        # send user registration signal
        signals.user_registered.send(sender=self, user=user)
        
        # check if there was a token group invite associated with the signup
        invite_token = self.request.POST.get('invite_token', None)
        if invite_token:
            invite = get_object_or_None(CosinnusGroupInviteToken, token__iexact=invite_token, portal=CosinnusPortal.get_current())
            if not invite:
                messages.warning(self.request, _('The invite token you have used does not exist!'))
            elif not invite.is_active:
                messages.warning(self.request, _('Sorry, but the invite token you have used is not active yet or not active anymore!'))
            else:
                success = apply_group_invite_token_for_user(invite, user)
                if success:
                    messages.success(self.request, _('Token invitations applied. You are now a member of the associated projects/groups!'))
                else:
                    messages.error(self.request, _('There was an error while processing your invites. Some of your invites may not have been applied.'))
        
        if getattr(settings, 'COSINNUS_SHOW_WELCOME_SETTINGS_PAGE', True):
            # add redirect to the welcome-settings page, with priority so that it is shown as first one
            profile.add_redirect_on_next_page(redirect_with_next(reverse('cosinnus:welcome-settings'), self.request), message=None, priority=True)
        
        return ret
    
    def dispatch(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            messages.info(self.request, _('You are already logged in!'))
            return redirect('/')
        return super(UserCreateView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UserCreateView, self).get_context_data(**kwargs)
        context['submit_label'] = _('Create')
        return context

user_create = check_honeypot(UserCreateView.as_view())


class WelcomeSettingsView(RequireLoggedInMixin, TemplateView):
    """ A welcome settings page that saves the two most important privacy aspects:
        the global notification setting and the userprofile visibility setting. """
    
    template_name = 'cosinnus/user/welcome_settings.html'
    message_success = _('Your privacy settings were saved. Welcome!')

    def post(self, request, *args, **kwargs):
        self.get_data()
        with transaction.atomic():
            # save language preference:
            notification_setting = request.POST.get('notification_setting', None)
            if notification_setting is not None and int(notification_setting) in (choice for choice, label in self.notification_choices):
                self.notification_setting.setting = int(notification_setting)
                self.notification_setting.save()
            # save visibility setting:
            visibility_setting = request.POST.get('visibility_setting', None)
            if visibility_setting is not None and int(visibility_setting) in (choice for choice, label in self.visibility_choices):
                self.media_tag.visibility = int(visibility_setting)
                self.media_tag.save()
        
        messages.success(request, self.message_success)
        if getattr(settings, 'COSINNUS_USE_V2_DASHBOARD', False) or \
            (getattr(settings, 'COSINNUS_USE_V2_DASHBOARD_ADMIN_ONLY', False) and self.request.user.is_superuser):
            redirect_url = reverse('cosinnus:user-dashboard')
        else:
            redirect_url = get_cosinnus_group_model().objects.get(slug=getattr(settings, 'NEWW_FORUM_GROUP_SLUG')).get_absolute_url() if hasattr(settings, 'NEWW_FORUM_GROUP_SLUG') else '/'
        redirect_url = redirect_next_or(self.request, redirect_url)
        return HttpResponseRedirect(redirect_url)
    
    def get_context_data(self, **kwargs):
        context = super(WelcomeSettingsView, self).get_context_data(**kwargs)
        #profile_model = get_user_profile_model()
        self.get_data()
        context.update({
            'visibility_setting': self.media_tag.visibility,
            'visibility_choices': self.visibility_choices,
            'notification_choices': self.notification_choices,
            'notification_setting': self.notification_setting.setting,
        })
        return context
    
    def get_data(self):
        self.media_tag = self.request.user.cosinnus_profile.media_tag
        self.visibility_choices = self.media_tag.VISIBILITY_CHOICES
        self.notification_setting = GlobalUserNotificationSetting.objects.get_object_for_user(self.request.user)
        # exclude the "individual" option, as this can only be set in notification preferences
        self.notification_choices = [choice for choice in self.notification_setting.SETTING_CHOICES if choice[0] != self.notification_setting.SETTING_GROUP_INDIVIDUAL]
        
welcome_settings = WelcomeSettingsView.as_view()


class CosinnusGroupInviteTokenEnterView(TemplateView):
    """ A welcome settings page that saves the two most important privacy aspects:
        the global notification setting and the userprofile visibility setting. """
    
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
    """ A welcome settings page that saves the two most important privacy aspects:
        the global notification setting and the userprofile visibility setting. """
    
    template_name = 'cosinnus/user/group_invite_token.html'
    message_success = _('Token invitations applied. You are now a member of the associated projects/groups!')
    
    def dispatch(self, request, *args, **kwargs):
        self.token = kwargs.get('token', None)
        self.invite = get_object_or_None(CosinnusGroupInviteToken, token__iexact=self.token, portal=CosinnusPortal.get_current())
        if not self.token or not self.invite:
            messages.error(self.request, _('The invite token you have used does not exist!'))
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
                messages.error(request, _('There was an error while processing your invites. Some of your invites may not have been applied.'))
            return HttpResponseRedirect(redirect_url)
        else:
            return HttpResponseRedirect('.')
    
    def get_context_data(self, **kwargs):
        context = super(CosinnusGroupInviteTokenView, self).get_context_data(**kwargs)
        if not self.invite.is_active:
            messages.warning(self.request, _('Sorry, but the invite token you have used is not active yet or not active anymore!'))
        elif not self.invite_groups:
            messages.warning(self.request, _('Sorry, but the invite token you have used does not seem to be valid!'))
        else:
            context.update({
                'token': self.token,
                'invite': self.invite,
                'invite_groups': self.invite_groups,
            })
        return context
        
group_invite_token_view = CosinnusGroupInviteTokenView.as_view()


def apply_group_invite_token_for_user(group_invite_token, user):
    """ Applies a `CosinnusGroupInviteToken` for a user, making them a member (if not already) of all groups
        determined by the invite token object. 
        @return: True if the user became member of all the groups, False if there was an error """
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
                logger.error('Error when trying to apply a token group invite', 
                         extra={'exception': force_text(e), 'user': user, 'group': group, 'token': group_invite_token.token})
                success = False
        
    return success


def _check_user_approval_permissions(request, user_id):
    """ Permission checks for user approval/denial views """
    if not request.method=='GET':
        return HttpResponseNotAllowed(['GET'])
    
    if not request.user.is_authenticated:
        return redirect_to_not_logged_in(request)
    elif not request.user.id in CosinnusPortal.get_current().admins:
        return redirect_to_403(request)
    return None


def approve_user(request, user_id):
    """ Approves an inactive, registration pending user and sends out an email to let them know """
    error = _check_user_approval_permissions(request, user_id)
    if error:
        return error
    
    try:
        user = USER_MODEL.objects.get(id=user_id)
    except USER_MODEL.DoesNotExist:
        messages.error(request, _('The user account you were looking for does not exist! Their registration was probably already denied.'))
        return redirect(reverse('cosinnus:user-list'))
    
    if user.is_active:
        messages.success(request, _('The user account was already approved, but thank you anyway!'))
        return redirect(reverse('cosinnus:user-list'))
    
    user.is_active = True
    user.save()
    
    # message user for accepeted request
    data = get_common_mail_context(request)
    data.update({
        'user': user,
    })
    template = 'cosinnus/mail/user_registration_approved.html'
    
    # if a welcome email text is set in the portal in admin, send that text instead of the default template
    portal = CosinnusPortal.get_current()
    welcome_text = getattr(portal, 'welcome_email_text', None) or '' 
    welcome_text = force_text(welcome_text).strip()
    if welcome_text:
        template = None
        data.update({
           'content': portal.welcome_email_text,
        })
    
    subj_user = render_to_string('cosinnus/mail/user_registration_approved_subj.txt', data)
    send_mail_or_fail_threaded(user.email, subj_user, template, data)
    
    
    messages.success(request, _('Thank you for approving user %(username)s (%(email)s)! An introduction-email was sent out to them and they can now log in to the site.') \
                     % {'username':full_name_force(user), 'email': user.email})
    return redirect(reverse('cosinnus:user-list'))



def deny_user(request, user_id):
    """ Deny a registration pending user. Sends out an email letting them know, then deletes the pending user account.
        Cannot be done for users that are active. """
    error = _check_user_approval_permissions(request, user_id)
    if error:
        return error
    
    try:
        user = USER_MODEL.objects.get(id=user_id)
    except USER_MODEL.DoesNotExist:
        messages.error(request, _('The user account you were looking for does not exist! Their registration was probably already denied.'))
        return redirect(reverse('cosinnus:user-list'))
    
    if user.is_active:
        messages.warning(request, _('The user account %(username)s (%(email)s) was already approved, so you cannot deny the registration! If this is a problem, you may want to deactivate the user manually from the admin interface.') \
                         % {'username':full_name_force(user), 'email': user.email})
        return redirect(reverse('cosinnus:user-list'))
    
    
    # message user for denied request
    admins = get_user_model().objects.filter(id__in=CosinnusPortal.get_current().admins)
    data = get_common_mail_context(request)
    data.update({
        'user': user,
        'admins': admins,
    })
    subj_user = render_to_string('cosinnus/mail/user_registration_denied_subj.txt', data)
    send_mail_or_fail_threaded(user.email, subj_user, 'cosinnus/mail/user_registration_denied.html', data)
    
    
    messages.success(request, _('You have denied the join request of %(username)s (%(email)s)! An email was sent to let them know.') \
                     % {'username':full_name_force(user), 'email': user.email})
    user.delete()
    return redirect(reverse('cosinnus:user-list'))
    

def verifiy_user_email(request, email_verification_param):
    """ Verify an email by comparing a token sent only to this email with the one saved in the user profile during registration (or email change) """
    user_id, token = email_verification_param.split('-', 1)
    
    try:
        user_id
        user = USER_MODEL.objects.get(id=user_id)
    except (USER_MODEL.DoesNotExist, ValueError,):
        messages.error(request, _('The user account you were looking for does not exist! Your registration was probably already denied or the email token has expired.'))
        return redirect(reverse('login'))
    
    profile = user.cosinnus_profile
    target_email = profile.settings.get(PROFILE_SETTING_EMAIL_TO_VERIFY, None)
    target_token = profile.settings.get(PROFILE_SETTING_EMAIL_VERFICIATION_TOKEN, None)
    if not target_email or not target_token:
        messages.error(request, _('The email for this account seems to already have been confirmed!'))
        return redirect(reverse('login'))    
    
    if not token == target_token:
        messages.error(request, _('The link you supplied for the email confirmation is no longer valid!'))
        return redirect(reverse('login'))
    
    # check if target email doesn't already exist:
    if target_email and get_user_model().objects.filter(email__iexact=target_email).count():
        # duplicate email is bad
        messages.error(request, _('The email you are trying to confirm has already been confirmed or belongs to another user!'))
        return redirect(reverse('login'))
    
    # everything seems to be in order, swap the scrambled with the real email
    with transaction.atomic():
        user.email = target_email
        user.save()
        del profile.settings[PROFILE_SETTING_EMAIL_TO_VERIFY]
        del profile.settings[PROFILE_SETTING_EMAIL_VERFICIATION_TOKEN]
        profile.save()
    
    if user.is_active:
        messages.success(request, _('Your email address %(email)s was successfully confirmed! Welcome to the community!') % {'email': user.email})
        user.backend = 'cosinnus.backends.EmailAuthBackend'
        login(request, user)
        return redirect(reverse('cosinnus:map'))
    else:
        messages.success(request, _('Your email address %(email)s was successfully confirmed! However, you account is not active yet and will have to be approved by an administrator before you can log in. We will send you an email as soon as that happens!') % {'email': user.email})
        return redirect(reverse('login'))
    

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
        return reverse('cosinnus:profile-detail',
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


def password_change_proxy(request, *args, **kwargs):
    """ Proxies the django.contrib.auth view. Only lets a user see the form or POST to it
        if the user is not a member of an integrated portal. """
    user = request.user
    if user.is_authenticated and check_user_integrated_portal_member(user):
        return TemplateResponse(request, 'cosinnus/registration/password_cannot_be_changed_page.html')
    return PasswordChangeView.as_view(*args, **kwargs)(request)


class CosinnusPasswordResetForm(PasswordResetForm):
    
    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
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
    """ Proxies the django.contrib.auth view. Only send a password reset mail
        if the email doesn't belong to a user that is a member of an integrated portal. """
    if request.method == 'POST':
        email = request.POST.get('email', None)
        user = None
        if email:
            try:
                user = USER_MODEL.objects.get(email=email, is_active=True)
            except USER_MODEL.DoesNotExist:
                pass
        if user and check_user_integrated_portal_member(user):
            return TemplateResponse(request, 'cosinnus/registration/password_cannot_be_reset_page.html')
    kwargs.update({
        'form_class': CosinnusPasswordResetForm,
    })
    return PasswordResetView.as_view(*args, **kwargs)(request)


def set_user_email_to_verify(user, new_email, request=None, user_has_just_registered=True):
    """ Sets the profile variables for a user to confirm a pending email, 
        and sends out an email with a verification URL to the user. 
        @param user_has_just_registered: If this True, a welcome email will be sent. 
            If False, an email change email will be sent. """
    
    # the verification param for the URL consists of <user-id>-<uuid>, where the uuid is saved to the user's profile
    a_uuid = uuid1()
    verification_url_param = '%d-%s' % (user.id, a_uuid)
    user.cosinnus_profile.settings[PROFILE_SETTING_EMAIL_TO_VERIFY] = new_email
    user.cosinnus_profile.settings[PROFILE_SETTING_EMAIL_VERFICIATION_TOKEN] = a_uuid
    user.cosinnus_profile.save()
    
    # message user for email verification
    if request:
        data = get_common_mail_context(request)
        data.update({
            'user':user,
            'user_email':new_email,
            'verification_url_param':verification_url_param,
            'next': redirect_with_next('', request),
        })
        template = 'cosinnus/mail/user_email_verification%s.html' % ('_onchange' if not user_has_just_registered else '')
        
        data.update({
            'content': render_to_string(template, data),
        })
        subj_user = render_to_string('cosinnus/mail/user_email_verification%s_subj.txt' % ('_onchange' if not user_has_just_registered else ''), data)
        send_mail_or_fail_threaded(new_email, subj_user, None, data)
        


def user_api_me(request):
    """ Returns a JSON dict of publicly available user data about the currently logged-in user.
        Returens {} if no user is logged in this session. """
    data = {}
    if request.user.is_authenticated:
        user = request.user
        user_societies = CosinnusSociety.objects.get_for_user(request.user)
        user_projects = CosinnusProject.objects.get_for_user(request.user)
        
        data.update({
            'username': user.username,
            'id': user.id,
            'first_name': user.first_name or '',
            'last_name': user.last_name or '',
            'avatar_url': CosinnusPortal.get_current().get_domain() + user.cosinnus_profile.get_avatar_thumbnail_url(), 
            'groups': [society.slug for society in user_societies],
            'projects': [project.slug for project in user_projects],
        })
    
    return JsonResponse(data)


def add_email_to_blacklist(request, email, token):
    """ Adds an email to the email blacklist. Used for generating list-unsubscribe links in our emails.
        Use `email_blacklist_token_generator.make_token(email)` to generate a token. """
    
    if not is_email_valid(email):
        messages.error(request, _('The unsubscribe link you have clicked does not seem to be valid!') + ' (1)')
        return render(request, 'cosinnus/common/200.html')
    
    if not email_blacklist_token_generator.check_token(email, token):
        messages.error(request, _('The unsubscribe link you have clicked does not seem to be valid!') + ' (2)')
        return render(request, 'cosinnus/common/200.html')
    
    GlobalBlacklistedEmail.add_for_email(email)
    messages.success(request, _('We have unsubscribed your email "%(email)s" from our mailing list. You will not receive any more emails from us!') 
        % {'email': email})
    
    return render(request, 'cosinnus/common/200.html')


def accept_updated_tos(request):
    """ A bare-bones ajax endpoint to save a user's accepted ToS settings.
        The frontend doesn't care about a return values, so we don't either 
        (on fail, the user will just see another popup on next request). """
    if request.method != 'POST':
        return HttpResponseNotAllowed('POST')
    if not request.user.is_authenticated:
        return HttpResponseForbidden('Must be logged in!')
    cosinnus_profile = request.user.cosinnus_profile
    
    form = TermsOfServiceFormFields(request.POST)
    if form.is_valid():
        # set the user's tos_accepted flag to true and date to now
        cosinnus_profile.settings['tos_accepted'] = True
        cosinnus_profile.settings['tos_accepted_date'] = now()
        # set the newsletter opt-in
        if settings.COSINNUS_USERPROFILE_ENABLE_NEWSLETTER_OPT_IN:
            cosinnus_profile.settings['newsletter_opt_in'] = form.cleaned_data.get('newsletter_opt_in')
        cosinnus_profile.save()
        return HttpResponse('Ok')
    else: 
        logger.warning('Could not save a user\'s updated ToS settings.', extra={'errors': form.errors, 'post-data': request.POST})
        return HttpResponseServerError('Failed')

    


@receiver(userprofile_ceated)
def convert_email_group_invites(sender, profile, **kwargs):
    """ Converts all `CosinnusUnregisterdUserGroupInvite` to `CosinnusGroupMembership` pending invites
        for a user after registration. If there were any, also adds an entry to the user's profile's visit-next setting. """
    # TODO: caching?
    user = profile.user
    invites = CosinnusUnregisterdUserGroupInvite.objects.filter(email=get_newly_registered_user_email(user))
    if invites:
        with transaction.atomic():
            for invite in invites:
                # skip inviting to auto-invite groups, users are in them automatically
                if invite.group.slug in settings.NEWW_DEFAULT_USER_GROUPS:
                    continue
                CosinnusGroupMembership.objects.create(group=invite.group, user=user, status=MEMBERSHIP_INVITED_PENDING)
            # trigger translation indexing
            _('Welcome! You were invited to the following projects and groups. Please click the dropdown button to accept or decline the invitation for each of them!')
            msg = 'Welcome! You were invited to the following projects and groups. Please click the dropdown button to accept or decline the invitation for each of them!'
            # create a user-settings-entry
            profile.add_redirect_on_next_page(reverse('cosinnus:invitations'), msg)
            # we actually do not delete the invites here yet, for many reasons such as re-registers when email verification didn't work
            # the invites will be deleted upon first login using the `user_logged_in_first_time` signal


@receiver(userprofile_ceated)
def remove_user_from_blacklist(sender, profile, **kwargs):
    user = profile.user
    email = get_newly_registered_user_email(user)
    GlobalBlacklistedEmail.remove_for_email(email)
    

@receiver(userprofile_ceated)
def create_user_notification_setting(sender, profile, **kwargs):
    user = profile.user
    GlobalUserNotificationSetting.objects.get_object_for_user(user)
    

@receiver(user_logged_in)
def detect_first_user_login(sender, user, request, **kwargs):
    """ Used to send out the user_first_logged_in_first_time signal """
    profile = user.cosinnus_profile
    first_login = profile.settings.get(PROFILE_SETTING_FIRST_LOGIN, None)
    if not first_login:
        profile.settings[PROFILE_SETTING_FIRST_LOGIN] = force_text(user.last_login)
        profile.save(update_fields=['settings'])
        user_logged_in_first_time.send(sender=sender, user=user, request=request)
    

@receiver(user_logged_in_first_time)
def cleanup_user_after_first_login(sender, user, request, **kwargs):
    """ Cleans up pre-registration objects and settings """
    CosinnusUnregisterdUserGroupInvite.objects.filter(email=user.email).delete()


    
