# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _, LANGUAGE_SESSION_KEY

from cosinnus.conf import settings

from cosinnus.utils.context_processors import cosinnus as cosinnus_context
from cosinnus.utils.context_processors import settings as cosinnus_context_settings
from cosinnus.utils.urls import safe_redirect
from django.http.response import  HttpResponseNotFound,\
    HttpResponseForbidden, HttpResponseServerError
from django.template.loader import render_to_string
from django.contrib.auth.views import login, logout

class IndexView(RedirectView):
    url = reverse_lazy('cosinnus:group-list')

index = IndexView.as_view()

"""
class PermissionDeniedView(TemplateView):
    template_name = '403.html'
    
view_403 = PermissionDeniedView.as_view()

class NotFoundView(TemplateView):
    template_name = '404.html'
    
view_404 = NotFoundView.as_view()
"""

def _get_bare_cosinnus_context(request):
    context = {
        'request': request,
        'user': request.user,
    }
    context.update(cosinnus_context(request))
    context.update(cosinnus_context_settings(request))
    return context


def view_403(request):
    content = render_to_string('cosinnus/common/403.html', _get_bare_cosinnus_context(request))
    return HttpResponseForbidden(content)

def view_404(request):
    content = render_to_string('cosinnus/common/404.html', _get_bare_cosinnus_context(request))
    return HttpResponseNotFound(content)

def view_500(request):
    content = render_to_string('cosinnus/common/500.html')
    return HttpResponseServerError(content)


class SwitchLanguageView(RedirectView):
    
    permanent = False
    
    def get(self, request, *args, **kwargs):
        language = kwargs.pop('language', None)
        
        if not language or language not in dict(settings.LANGUAGES).keys():
            messages.error(request, _('The language "%s" is not supported' % language))
        else:
            request.session[LANGUAGE_SESSION_KEY] = language
            request.session['django_language'] = language
            request.LANGUAGE_CODE = language
        #messages.success(request, _('Language was switched successfully.'))
        
        return super(SwitchLanguageView, self).get(request, *args, **kwargs)
        
    def get_redirect_url(self, **kwargs):
        return safe_redirect(self.request.GET.get('next', self.request.META.get('HTTP_REFERER', '/')), self.request)
        

switch_language = SwitchLanguageView.as_view()


def cosinnus_login(request, **kwargs):
    """ Wraps the django login view to set the "wp_user_logged_in" cookie on logins """
    response = login(request, **kwargs)
    if request.method == 'POST' and not request.user.is_anonymous():
        response.set_cookie('wp_user_logged_in', 1, 60*60*24*30) # 30 day expiry
    return response

def cosinnus_logout(request, **kwargs):
    """ Wraps the django logout view to delete the "wp_user_logged_in" cookie on logouts
        (this seems to only clear the value of the cookie and not completely delete it!) """
    response = logout(request, **kwargs)
    if request.user.is_anonymous():
        response.delete_cookie('wp_user_logged_in')
    return response

