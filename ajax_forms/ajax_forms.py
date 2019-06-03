from django import forms
from django.views.generic.base import View
from django.http.response import HttpResponseForbidden, JsonResponse,\
    HttpResponseBadRequest
from django.core.validators import MaxValueValidator, MinValueValidator

import logging
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string

logger = logging.getLogger('cosinnus')


class AjaxEnabledFormViewBaseMixin(object):
    
    ajax_form_partial = None # '/path/to/template.html'
    ajax_result_partial = None # '/path/to/template.html'


class AjaxFormsCreateViewMixin(AjaxEnabledFormViewBaseMixin):
    
    def form_valid(self, form):
        if not self.request.is_ajax():
            return super(AjaxFormsCreateViewMixin, self).form_valid(self, form)
        
        data = {
            'result_html': render_to_string(self.ajax_result_partial, {'object': self.object}),
            'new_form_html': self.render_new_form(self.ajax_form_partial),
            'ajax-form-id': self.request.POST.get('ajax-form-id')
        }
        return JsonResponse(data)
    
    def render_new_form(self, template):
        # render a fresh form using only the `template` partial
        return 'TODO'
    