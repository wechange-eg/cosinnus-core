# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
from django.http import HttpResponse, HttpResponseBadRequest
from django.core.exceptions import ImproperlyConfigured
from rest_framework.response import Response
from rest_framework.renderers import JSONRenderer
from django.http.request import QueryDict
import urllib


class BaseAjaxableResponseMixin(object):
    """
    Base mixin to add AJAX support to GET-ting views.
    
    Do not use this Mixin, but rather the specialized mixins 
    (e.g. ListAjaxableResponseMixin, DetailAjaxableResponseMixin)
    """
    # This is set via the context in urls.py and prevents accessing the JSONified
    # version of the mixing view via a non-ajax-url path
    is_ajax_request_url = False
    # Django restframework serializer class for the object of the form
    serializer_class = None

    def get(self, request, *args, **kwargs):
        if self.is_ajax_request_url:

            if not request.is_ajax():
                return HttpResponseBadRequest()
            response = super(BaseAjaxableResponseMixin, self).get(request, *args, **kwargs)

            if not self.serializer_class:
                raise ImproperlyConfigured("Missing property serialzer_class for object " +
                                            str(super(BaseAjaxableResponseMixin, self))
            )

            context = {'request': self.request}
            serializer = self.serializer_class(response.context_data['object_list'],
                                          many=True, context=context)

            response = Response(serializer.data)
            response.accepted_renderer = JSONRenderer()
            response.accepted_media_type = response.accepted_renderer.media_type
            response.renderer_context = context
            return response

        else:
            return super(BaseAjaxableResponseMixin, self).get(request, *args, **kwargs)

        def get_serializable_content(self):
            raise NotImplementedError("Subclasses must implement this method")

class ListAjaxableResponseMixin(BaseAjaxableResponseMixin):
    """ 
    Mixin to add AJAX support to a ListView.
    """
    def get_serializable_content(self):
        return self.object_list


class DetailAjaxableResponseMixin(BaseAjaxableResponseMixin):
    """ 
    Mixin to add AJAX support to a DetailView.
    """
    def get_serializable_content(self):
        return self.object

class AjaxableFormMixin(object):
    """
    Mixin to add AJAX support to a form.
    Must be used with an object-based FormView (e.g. CreateView)
    """
    # This is set via the context in urls.py and prevents accessing the JSONified
    # version of the mixing view via a non-ajax-url path
    is_ajax_request_url = False
    # Django restframework serializer class for the object of the form
    serializer_class = None

    def render_to_json_response(self, context, **response_kwargs):
        if self.is_ajax_request_url:
            data = json.dumps(context)
            response_kwargs['content_type'] = 'application/json'
            return HttpResponse(data, **response_kwargs)
        else:
            return HttpResponseBadRequest()

    def post(self, request, *args, **kwargs):
        if self.is_ajax_request_url:
            if not request.is_ajax():
                return HttpResponseBadRequest()

            # patch the ajax-post body data into the POST field
            body_data = urllib.urlencode(json.loads(request.body, encoding=request.encoding))
            request._post = QueryDict(body_data, encoding=request.encoding)
            self.request = request

        return super(AjaxableFormMixin, self).post(request, *args, **kwargs)

    def form_invalid(self, form):
        if self.is_ajax_request_url:
            response = super(AjaxableFormMixin, self).form_invalid(form)
            if self.is_ajax_request_url and self.request.is_ajax():
                return self.render_to_json_response(form.errors, status=400)
            else:
                return response
        else:
            return super(AjaxableFormMixin, self).form_invalid(form)

    def form_valid(self, form):
        if self.is_ajax_request_url:
            # We make sure to call the parent's form_valid() method because
            # it might do some processing (in the case of CreateView, it will
            # call form.save() for example).
            response = super(AjaxableFormMixin, self).form_valid(form)
            if self.is_ajax_request_url and self.request.is_ajax():
                data = {
                    'pk': self.object.pk,
                    'id': self.object.id,
                }
                return self.render_to_json_response(data)
            else:
                return response
        else:
            return super(AjaxableFormMixin, self).form_valid(form)
