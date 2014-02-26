# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from django.http import HttpResponse, HttpResponseBadRequest


class AjaxableResponseMixin(object):
    """
    Mixin to add AJAX support to a form.
    Must be used with an object-based FormView (e.g. CreateView)
    """
    # This is set via the context in urls.py and prevents accessing the JSONified
    # version of the mixing view via a non-ajax-url path
    is_ajax_request_url = False

    def get(self, request, *args, **kwargs):
        if self.is_ajax_request_url and not request.is_ajax():
            return HttpResponseBadRequest()
        return super(AjaxableResponseMixin, self).get(request, *args, **kwargs)

    def render_to_json_response(self, context, **response_kwargs):
        if self.is_ajax_request_url:
            data = json.dumps(context)
            response_kwargs['content_type'] = 'application/json'
            return HttpResponse(data, **response_kwargs)
        else:
            return HttpResponseBadRequest()

    def form_invalid(self, form):
        response = super(AjaxableResponseMixin, self).form_invalid(form)
        if self.is_ajax_request_url and self.request.is_ajax():
            return self.render_to_json_response(form.errors, status=400)
        else:
            return response

    def form_valid(self, form):
        # We make sure to call the parent's form_valid() method because
        # it might do some processing (in the case of CreateView, it will
        # call form.save() for example).
        response = super(AjaxableResponseMixin, self).form_valid(form)
        if self.is_ajax_request_url and self.request.is_ajax():
            data = {
                'pk': self.object.pk,
            }
            return self.render_to_json_response(data)
        else:
            return response
