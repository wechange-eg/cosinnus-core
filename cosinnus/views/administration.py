# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin

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

from cosinnus.templatetags.cosinnus_tags import textfield
from cosinnus.utils.html import render_html_with_variables
from cosinnus.core.mail import send_html_mail_threaded
from cosinnus.models.group import CosinnusGroup


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
        context['receipients'] = len(self._get_recipients_from_tags())
        return context

    def _get_recipients_from_tags(self):
        managed_tags = self.object.managed_tags.all()
        group_type = ContentType.objects.get(app_label='cosinnus', model='cosinnusgroup')
        profile_type = ContentType.objects.get(app_label='cosinnus', model='userprofile')
        users = []
        for tag in managed_tags:
            group_tags = tag.assignments.filter(content_type=group_type)
            for group_tag in group_tags:
                for user in group_tag.target_object.users.all():
                    users.append(user)

            profile_tags = tag.assignments.filter(content_type=profile_type)
            for profile_tag in profile_tags:
                users.append(profile_tag.target_object.user)
        user_set = set(users)
        return list(user_set)

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

    def dispatch(self, request, *args, **kwargs):
        if not check_user_superuser(request.user):
            raise PermissionDenied('You do not have permission to access this page.')
        return super().dispatch(request, *args, **kwargs)

user_list = UserListView.as_view()

class UserUpdateView(SuccessMessageMixin, UpdateView):
    model = get_user_model()
    form_class = UserAdminForm
    template_name = 'cosinnus/administration/user_form.html'
    pk_url_kwarg = 'user_id'
    success_url = reverse_lazy('cosinnus:administration-users')
    success_message = _("User successfully updated!")

    def dispatch(self, request, *args, **kwargs):
        if not check_user_superuser(request.user):
            raise PermissionDenied('You do not have permission to access this page.')
        return super().dispatch(request, *args, **kwargs)

user_update = UserUpdateView.as_view()


class UserCreateView(SuccessMessageMixin, CreateView):
    model = get_user_model()
    form_class = UserAdminForm
    template_name = 'cosinnus/administration/user_form.html'
    success_url = reverse_lazy('cosinnus:administration-users')
    success_message = _("User successfully created!")

    def dispatch(self, request, *args, **kwargs):
        if not check_user_superuser(request.user):
            raise PermissionDenied('You do not have permission to access this page.')
        return super().dispatch(request, *args, **kwargs)

user_add = UserCreateView.as_view()
