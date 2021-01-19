# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.views.generic.edit import CreateView, FormView, UpdateView
from django.views.generic.list import ListView
from cosinnus.utils.permissions import check_user_superuser
from django.core.exceptions import PermissionDenied
from django.views.generic.base import TemplateView
from cosinnus.forms.administration import (UserWelcomeEmailForm,
NewsletterForManagedTagsForm, UserAdminForm)
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.newsletter import Newsletter
from django.urls.base import reverse
from cosinnus.views.user import _send_user_welcome_email_if_enabled
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import get_user_model

from cosinnus.views.profile import UserProfileUpdateView
from cosinnus.templatetags.cosinnus_tags import textfield
from cosinnus.utils.permissions import check_user_can_receive_emails
from cosinnus.utils.html import render_html_with_variables
from cosinnus.core.mail import send_html_mail_threaded
from cosinnus.models.group import CosinnusGroup
from cosinnus.models.managed_tags import CosinnusManagedTagAssignment
from cosinnus.views.user import email_first_login_token_to_user
from cosinnus.conf import settings
from cosinnus.models.profile import PROFILE_SETTING_LOGIN_TOKEN_SENT


class AdministrationView(TemplateView):
    
    template_name = 'cosinnus/administration/administration.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not check_user_superuser(request.user):
            raise PermissionDenied('You do not have permission to access this page.')
        return super(AdministrationView, self).dispatch(request, *args, **kwargs)

administration = AdministrationView.as_view()


class UserWelcomeEmailEditView(FormView):
    
    form_class = UserWelcomeEmailForm
    template_name = 'cosinnus/administration/welcome_email.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not check_user_superuser(request.user):
            raise PermissionDenied('You do not have permission to access this page.')
        self.portal = CosinnusPortal.get_current()
        if request.GET.get('send_test', False) == '1':
            _send_user_welcome_email_if_enabled(self.request.user, force=True)
            messages.success(self.request, _('Test email sent!'))
            return redirect(self.get_success_url())
        return super(UserWelcomeEmailEditView, self).dispatch(request, *args, **kwargs)
    
    def get_initial(self, *args, **kwargs):
        initial = super(UserWelcomeEmailEditView, self).get_initial(*args, **kwargs)
        initial.update({
            'is_active': self.portal.welcome_email_active,
            'email_text': self.portal.welcome_email_text,
        })
        return initial
    
    def get_context_data(self, *args, **kwargs):
        context = super(UserWelcomeEmailEditView, self).get_context_data(*args, **kwargs)
        context.update({
            'email_text': self.portal.welcome_email_text,
        })
        return context
    
    def form_valid(self, form):
        self.form = form
        self.portal.welcome_email_active = form.cleaned_data.get('is_active', False)
        self.portal.welcome_email_text = form.cleaned_data.get('email_text', '')
        self.portal.save(update_fields=['welcome_email_active', 'welcome_email_text'])
        return super(UserWelcomeEmailEditView, self).form_valid(form)
    
    def get_success_url(self):
        return reverse('cosinnus:administration-welcome-email')
    

welcome_email_edit = UserWelcomeEmailEditView.as_view()


class ManagedTagsNewsletterMixin:

    def dispatch(self, request, *args, **kwargs):
        if not check_user_superuser(request.user):
            raise PermissionDenied('You do not have permission to access this page.')
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('cosinnus:administration-managed-tags-newsletter-update',args=(self.object.id,))


class ManagedTagsNewsletterListView(ManagedTagsNewsletterMixin, ListView):
    model = Newsletter
    template_name = 'cosinnus/administration/newsletter_list.html'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.order_by('-sent')

managed_tags_newsletters = ManagedTagsNewsletterListView.as_view()


class ManagedTagsNewsletterCreateView(SuccessMessageMixin,
                                     ManagedTagsNewsletterMixin,
                                     CreateView):
    model = Newsletter
    form_class = NewsletterForManagedTagsForm
    template_name = 'cosinnus/administration/newsletter_form.html'
    success_message = _("Newsletter successfully created!")


managed_tags_newsletter_create = ManagedTagsNewsletterCreateView.as_view()


class ManagedTagsNewsletterUpdateView(ManagedTagsNewsletterMixin,
                                      UpdateView):
    model = Newsletter
    form_class = NewsletterForManagedTagsForm
    template_name = 'cosinnus/administration/newsletter_form.html'
    pk_url_kwarg = 'newsletter_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['receipients'] = self._get_recipients_from_tags()
        return context

    def _get_recipients_from_tags(self):
        tags = self.object.managed_tags.all()
        assignments = CosinnusManagedTagAssignment.objects.filter(managed_tag__in=tags)
        
        group_type = ContentType.objects.get(
            app_label='cosinnus', model='cosinnusgroup')
        profile_type = ContentType.objects.get(
            app_label='cosinnus', model='userprofile')
        group_ids = assignments.filter(
            content_type=group_type).values_list('object_id', flat=True)
        profile_ids = assignments.filter(
            content_type=profile_type).values_list('object_id', flat=True)
        
        tag_users = get_user_model().objects.filter(
            Q(cosinnus_groups__id__in=group_ids) | Q(cosinnus_profile__id__in=profile_ids)).distinct()

        users = []
        for user in tag_users:
            if (check_user_can_receive_emails(user)):
                # if the newsletter opt-in is enabled, only send the newsletter to users
                # who have the option enabled in their profiles
                if settings.COSINNUS_USERPROFILE_ENABLE_NEWSLETTER_OPT_IN and not \
                        user.cosinnus_profile.settings.get('newsletter_opt_in', False):
                    continue
                users.append(user)

        return users

    def _send_newsletter(self, recipients):
        subject = self.object.subject
        text = self.object.body
        for recipient in recipients:
            text = textfield(render_html_with_variables(recipient, text))
            send_html_mail_threaded(recipient, subject, text)

    def _copy_newsletter(self):
        subject = '{} (copy)'.format(self.object.subject)
        body = self.object.body
        copy = Newsletter.objects.create(
            subject=subject,
            body=body
        )
        for managed_tag in self.object.managed_tags.all():
            copy.managed_tags.add(managed_tag)
        return copy

    def form_valid(self, form):
        self.object = form.save()
        if 'send_newsletter' in self.request.POST:
            recipients = self._get_recipients_from_tags()
            self._send_newsletter(recipients)
            self.object.sent = timezone.now()
            self.object.save()
            messages.add_message(self.request, messages.SUCCESS, _('Newsletter sent.'))
        elif 'send_test_mail' in self.request.POST:
            self._send_newsletter([self.request.user])
            messages.add_message(self.request, messages.SUCCESS, _('Test email sent.'))
        elif 'copy_newsletter' in self.request.POST:
            self.object = self._copy_newsletter()
            messages.add_message(self.request, messages.SUCCESS, _('Newsletter has been copied.'))
        else:
            messages.add_message(self.request, messages.SUCCESS, _('Newsletter has been updated.'))
        return HttpResponseRedirect(self.get_success_url())

managed_tags_newsletter_update = ManagedTagsNewsletterUpdateView.as_view()


class UserListView(ManagedTagsNewsletterMixin, ListView):
    model = get_user_model()
    template_name = 'cosinnus/administration/user_list.html'
    ordering = '-date_joined'
    paginate_by = 50

    def dispatch(self, request, *args, **kwargs):
        if not check_user_superuser(request.user):
            raise PermissionDenied('You do not have permission to access this page.')
        return super().dispatch(request, *args, **kwargs)

    def send_login_token(self, user):
        email_first_login_token_to_user(user)

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.GET.get('search'):
            search_string = self.request.GET.get('search')
            qs = qs.filter(Q(email__icontains=search_string) |
                           Q(first_name__icontains=search_string) |
                           Q(last_name__icontains=search_string) )
        return qs

    def get_context_data(self):
        context = super().get_context_data()
        context['total'] = self.get_queryset().count()
        return context


    def post(self, request, *args, **kwargs):
        search_string = ''
        if 'search' in self.request.POST and request.POST.get('search'):
            search_string = '?search={}'.format(request.POST.get('search'))
        if 'send_login_token' in self.request.POST:
            if self.request.POST.get('send_login_token') == '__all__':
                non_tokened_users = get_user_model().objects.filter(password__isnull=True, last_login__isnull=True)
                count = 0
                for user in non_tokened_users:
                    if not PROFILE_SETTING_LOGIN_TOKEN_SENT in user.cosinnus_profile.settings:
                        self.send_login_token(user)
                        count += 1
                messages.add_message(self.request, messages.SUCCESS, _('Login tokens to %(count)s users were sent.') % {'count': count})
            else:
                user_id = self.request.POST.get('send_login_token')
                user = get_user_model().objects.get(id=user_id)
                self.send_login_token(user)
                messages.add_message(self.request, messages.SUCCESS, _('Login token was sent to %(email)s.') % {'email': user.email})
        redirect_path = '{}{}'.format(request.path_info, search_string)
        return HttpResponseRedirect(redirect_path)

user_list = UserListView.as_view()

class AdminUserUpdateView(UserProfileUpdateView):
    template_name = 'cosinnus/administration/user_update_form.html'
    message_success = _('Die Änderungen wurden erfolgreich gespeichert.')

    disable_conditional_field_locking = True

    def dispatch(self, request, *args, **kwargs):
        if not check_user_superuser(request.user):
            raise PermissionDenied('You do not have permission to access this page.')
        return super().dispatch(request, *args, **kwargs)

    def get_form(self, *args, **kwargs):
        form = super(AdminUserUpdateView, self).get_form(*args, **kwargs)
        for field_name in form.forms['obj'].fields:
            field = form.forms['obj'].fields[field_name]
            field.required = False
        return form

    def post(self, request, *args, **kwargs):
        if 'send_login_token' in self.request.POST:
            user_id = self.request.POST.get('send_login_token')
            user = get_user_model().objects.get(id=user_id)
            email_first_login_token_to_user(user)
            messages.add_message(self.request, messages.SUCCESS, _('Login token was sent.'))
            return HttpResponseRedirect(request.path_info)
        else:
            return super().post(request, *args, **kwargs)

    def get_success_url(self):
        return self.request.path

    def get_form_kwargs(self, *args, **kwargs):
        form_kwargs = super(AdminUserUpdateView, self).get_form_kwargs(*args, **kwargs)
        form_kwargs.update({
            'obj__hidden_dynamic_fields_shown': True,
            'obj__readonly_dynamic_fields_enabled': True,
            'obj__user_admin_form_managed_tag_enabled': True,
        })
        return form_kwargs

user_update = AdminUserUpdateView.as_view()


class UserCreateView(SuccessMessageMixin, CreateView):
    model = get_user_model()
    form_class = UserAdminForm
    template_name = 'cosinnus/administration/user_create_form.html'
    success_url = reverse_lazy('cosinnus:administration-users')
    success_message = _("User successfully created!")

    def dispatch(self, request, *args, **kwargs):
        if not check_user_superuser(request.user):
            raise PermissionDenied('You do not have permission to access this page.')
        return super().dispatch(request, *args, **kwargs)

user_add = UserCreateView.as_view()
