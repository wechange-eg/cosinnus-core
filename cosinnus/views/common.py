# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _

from cosinnus.conf import settings

class IndexView(RedirectView):
    url = reverse_lazy('cosinnus:group-list')

index = IndexView.as_view()


class SwitchLanguageView(RedirectView):
    
    def get(self, request, *args, **kwargs):
        language = kwargs.pop('language', None)
        if not language or language not in dict(settings.LANGUAGES).keys():
            messages.error(request, _('The language "%s" is not supported' % language))
            
        request.session['django_language'] = language
        #messages.success(request, _('Language was switched successfully.'))
        
        return super(SwitchLanguageView, self).get(request, *args, **kwargs)
        
    def get_redirect_url(self, **kwargs):
        return self.request.GET.get('next', self.request.META.get('HTTP_REFERER', '/'))
        

switch_language = SwitchLanguageView.as_view()
