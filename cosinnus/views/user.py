# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.auth import get_user_model, login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from django.core.urlresolvers import reverse, reverse_lazy
from django.db import transaction
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _, get_language
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from cosinnus.core.decorators.views import staff_required, superuser_required,\
    redirect_to_not_logged_in, redirect_to_403
from cosinnus.forms.user import UserCreationForm, UserChangeForm
from cosinnus.views.mixins.ajax import patch_body_json_data
from cosinnus.utils.http import JSONResponse
from django.contrib import messages
from cosinnus.models.profile import get_user_profile_model,\
    PROFILE_SETTING_EMAIL_TO_VERIFY, PROFILE_SETTING_EMAIL_VERFICIATION_TOKEN
from cosinnus.models.tagged import BaseTagObject
from cosinnus.models.group import CosinnusPortal
from cosinnus.core.mail import MailThread, get_common_mail_context,\
    send_mail_or_fail_threaded
from django.template.loader import render_to_string
from django.http.response import HttpResponseNotAllowed
from django.shortcuts import redirect
from cosinnus.templatetags.cosinnus_tags import full_name_force
from django.contrib.auth.views import password_reset, password_change
from cosinnus.utils.permissions import check_user_integrated_portal_member
from django.template.context import RequestContext
from django.template.response import TemplateResponse
from django.core.paginator import Paginator
from cosinnus.views.mixins.group import EndlessPaginationMixin
from cosinnus.utils.user import filter_active_users
from uuid import uuid1
from django.utils.encoding import force_text


USER_MODEL = get_user_model()


def email_portal_admins(subject, template, data):
    mail_thread = MailThread()
    admins = get_user_model().objects.filter(id__in=CosinnusPortal.get_current().admins)
    
    for user in admins:
        mail_thread.add_mail(user.email, subject, template, data)
    mail_thread.start()


class UserListView(EndlessPaginationMixin, ListView):

    model = USER_MODEL
    template_name = 'cosinnus/user/user_list.html'
    items_template = 'cosinnus/user/user_list_items.html'
    paginator_class = Paginator
    
    def get_queryset(self):
        
        # get all users from this portal only        
        # we also exclude users who have never logged in
        all_users = filter_active_users(super(UserListView, self).get_queryset().filter(id__in=CosinnusPortal.get_current().members))
        
        if self.request.user.is_authenticated():
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
    success_url = reverse_lazy('login')
    template_name = 'cosinnus/registration/signup.html'

    message_success = _('User "%(user)s" was registered successfully. You can now log in using this username.')
    message_success_inactive = _('User "%(user)s" was registered successfully. The account will need to be approved before you can log in. We will send an email to your address "%(email)s" when this happens.')
    message_success_email_verification = _('User "%(user)s" was registered successfully. We will send an email to your address %(email)s" soon. You need to confirm the email address before you can log in.')
    
    def form_valid(self, form):
        ret = super(UserCreateView, self).form_valid(form)
        user = self.object
        
        # sanity check, retrieve the user's profile (will create it if it doesnt exist)
        profile = get_user_profile_model()._default_manager.get_for_user(user)
        
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
            
        return ret
    
    def dispatch(self, *args, **kwargs):
        if self.request.user.is_authenticated():
            messages.info(self.request, _('You are already logged in!'))
            return redirect('/')
        return super(UserCreateView, self).dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(UserCreateView, self).get_context_data(**kwargs)
        context['submit_label'] = _('Create')
        return context

user_create = UserCreateView.as_view()


def _check_user_approval_permissions(request, user_id):
    """ Permission checks for user approval/denial views """
    if not request.method=='GET':
        return HttpResponseNotAllowed(['GET'])
    
    if not request.user.is_authenticated():
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
        messages.success(request, _('Your email address %(email)s was successfully confirmed! You can now log in and get started!') % {'email': user.email})
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
    if user.is_authenticated() and check_user_integrated_portal_member(user):
        return TemplateResponse(request, 'cosinnus/registration/password_cannot_be_changed_page.html')
    return password_change(request, *args, **kwargs)


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
    return password_reset(request, *args, **kwargs)


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
        data.update({'user':user, 'user_email':new_email, 'verification_url_param':verification_url_param})
        subj_user = render_to_string('cosinnus/mail/user_email_verification%s_subj.txt' % ('_onchange' if not user_has_just_registered else ''), data)
        send_mail_or_fail_threaded(new_email, subj_user, 'cosinnus/mail/user_email_verification%s.html' \
                    % ('_onchange' if not user_has_just_registered else ''), data)
