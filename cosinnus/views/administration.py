# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.views.generic.edit import FormView
from cosinnus.utils.permissions import check_user_superuser
from django.core.exceptions import PermissionDenied
from django.views.generic.base import TemplateView
from cosinnus.forms.administration import UserWelcomeEmailForm
from cosinnus.models.group import CosinnusPortal
from django.urls.base import reverse
from cosinnus.views.user import _send_user_welcome_email_if_enabled
from django.shortcuts import redirect


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

