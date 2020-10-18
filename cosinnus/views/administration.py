# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import messages

from django.http import HttpResponseRedirect
from django.utils import timezone
from django.views.generic.edit import CreateView, FormView, UpdateView
from django.views.generic.list import ListView
from cosinnus.utils.permissions import check_user_superuser
from django.core.exceptions import PermissionDenied
from django.views.generic.base import TemplateView
from cosinnus.forms.administration import UserWelcomeEmailForm, NewsletterForGroupForm
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.newsletter import  Newsletter
from django.urls.base import reverse
from cosinnus.views.user import _send_user_welcome_email_if_enabled
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _

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


class GroupNewsletterMixin:

    def get_groups_as_options(self):
        portal = CosinnusPortal.get_current()
        groups = portal.groups.all()
        return [(group.id, group) for group in groups]

    def get_form_kwargs(self):
        form_kwargs = super().get_form_kwargs()
        form_kwargs['groups'] = self.get_groups_as_options()
        return form_kwargs

    def dispatch(self, request, *args, **kwargs):
        if not check_user_superuser(request.user):
            raise PermissionDenied('You do not have permission to access this page.')
        return super().dispatch(request, *args, **kwargs)


class GroupNewsletterListView(GroupNewsletterMixin, ListView):
    model = Newsletter
    template_name = 'cosinnus/administration/newsletter_list.html'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.order_by('-sent')

group_newsletters = GroupNewsletterListView.as_view()


class GroupNewsletterCreateView(GroupNewsletterMixin, CreateView):
    model = Newsletter
    form_class = NewsletterForGroupForm
    template_name = 'cosinnus/administration/newsletter_form.html'
    success_url = reverse_lazy('cosinnus:administration-group-newsletter')

group_newsletter_create = GroupNewsletterCreateView.as_view()


class GroupNewsletterUpdateView(GroupNewsletterMixin, UpdateView):
    model = Newsletter
    form_class = NewsletterForGroupForm
    template_name = 'cosinnus/administration/newsletter_form.html'
    pk_url_kwarg = 'newsletter_id'
    success_url = reverse_lazy('cosinnus:administration-group-newsletter')

    def _get_recipients_from_group(self):
        source = self.object.recipients_source
        if source.startswith('group'):
            group_id = int(source.split('@')[1])
            try:
                group = CosinnusGroup.objects.get(id=group_id)
                return group.actual_members
            except CosinnusGroup.DoesNotExist:
                return []
        return []

    def _send_newsletter(self, recipients):
        subject = self.object.subject
        text = self.object.body
        for recipient in recipients:
            text = textfield(render_html_with_variables(recipient, text))
            send_html_mail_threaded(recipient, subject, text)

    def form_valid(self, form):
        self.object = form.save()
        if 'send_newsletter' in self.request.POST:
            recipients = self._get_recipients_from_group()
            self._send_newsletter(recipients)
            self.object.sent = timezone.now()
            self.object.save()
            messages.add_message(self.request, messages.SUCCESS, _('Newsletter sent.'))
        elif 'send_test_mail' in self.request.POST:
            self._send_newsletter([self.request.user])
            messages.add_message(self.request, messages.SUCCESS, _('Test email sent.'))
        return HttpResponseRedirect(self.get_success_url())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        source = self.object.recipients_source
        if source.startswith('group'):
            group_id = int(source.split('@')[1])
            kwargs['group'] = group_id
        return kwargs

group_newsletter_update = GroupNewsletterUpdateView.as_view()
