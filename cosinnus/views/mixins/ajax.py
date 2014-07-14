# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import six

from django.contrib.messages.api import get_messages
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseBadRequest, QueryDict
from django.utils.encoding import force_text

from cosinnus.utils.http import JSONResponse


def patch_body_json_data(request):
    """
    Patch the ajax-post body data into the POST field
    """
    body = request.body
    encoding = request.encoding or 'utf-8'
    body = force_text(body, encoding=encoding)
    json_data = json.loads(body, encoding=request.encoding)

    querydict = QueryDict('', mutable=True)

    for k, v in six.iteritems(json_data):
        if v is None:
            querydict[k] = ''
        elif isinstance(v, dict):
            # If we find a dict we check if it is a nested object.
            # Every nested object must have an id.
            pk = v.get('id', None)
            if pk is not None:
                querydict[k] = force_text(pk)
            continue
        else:
            querydict[k] = force_text(v)

    request._post = querydict
    return request


class BaseAjaxableResponseMixin(object):
    """
    Base mixin to add AJAX support to GET-ting views.

    Do not use this mixin directly, but rather the specialized mixins (e.g.
    :class:`ListAjaxableResponseMixin`, :class:`DetailAjaxableResponseMixin`)
    """
    #: This is set via the context in urls.py and prevents accessing the
    #: JSONified version of the mixing view via a non-ajax-url path
    is_ajax_request_url = False

    #: Django restframework serializer class for the object of the form
    serializer_class = None

    # different for List/Detail view
    is_object_collection = False

    def get(self, request, *args, **kwargs):
        if self.is_ajax_request_url:
            # Prevent access to ajaxible paths from non-ajax requests
            if not request.is_ajax():
                return HttpResponseBadRequest("API calls do not supported direct access.")

            response = super(BaseAjaxableResponseMixin, self).get(request, *args, **kwargs)

            if not self.serializer_class:
                raise ImproperlyConfigured(
                    'Missing property serialzer_class for object "%s" '
                    '(needed by Ajax Mixins)' % self.__class__.__name__
                )

            context = {'request': self.request}
            serializer = self.serializer_class(self.get_serializable_content(),
                                               many=self.is_object_collection,
                                               context=context)
            return JSONResponse(serializer.data, status=response.status_code)

        else:
            return super(BaseAjaxableResponseMixin, self).get(request, *args, **kwargs)

        def get_serializable_content(self):
            raise NotImplementedError("Subclasses must implement this method")


class ListAjaxableResponseMixin(BaseAjaxableResponseMixin):
    """
    Mixin to add AJAX support to a ListView.
    """
    is_object_collection = True

    def get_serializable_content(self):
        return getattr(self, 'object_list', [])  # We need an iterable


class DetailAjaxableResponseMixin(BaseAjaxableResponseMixin):
    """
    Mixin to add AJAX support to a DetailView.
    """
    is_object_collection = False

    def get_serializable_content(self):
        return getattr(self, 'object', None)  # We need the object or None


class AjaxableFormMixin(object):
    """
    Mixin to add AJAX support to a form.

    Must be used with an object-based FormView (e.g. CreateView)
    """
    #: This is set via the context in urls.py and prevents accessing the
    #: JSONified version of the mixing view via a non-ajax-url path
    is_ajax_request_url = False

    #: Django restframework serializer class for the object of the form
    serializer_class = None

    def delete(self, request, *args, **kwargs):
        if self.is_ajax_request_url:
            if not request.is_ajax():
                return HttpResponseBadRequest()

            # from django.views.generic.DeleteView
            self.object = self.get_object()
            self.object.delete()
            # return an empty response to signify success, instead of redirecting
            return self.render_to_json_response({})

        return super(AjaxableFormMixin, self).delete(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if self.is_ajax_request_url:
            if not request.is_ajax():
                return HttpResponseBadRequest()

            request = self._patch_body_data_to_post(request)

        return super(AjaxableFormMixin, self).post(request, *args, **kwargs)

    def form_invalid(self, form):
        if self.is_ajax_request_url:
            response = super(AjaxableFormMixin, self).form_invalid(form)
            if self.is_ajax_request_url and self.request.is_ajax():
                # TODO: get the messages (as in form_valid()
                # and add them to the response, if that is wished)
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
                    'messages': [force_text(msg) for msg in get_messages(self.request)],
                }
                return self.render_to_json_response(data)
            else:
                return response
        else:
            return super(AjaxableFormMixin, self).form_valid(form)

    def render_to_json_response(self, context, **response_kwargs):
        if self.is_ajax_request_url:
            return JSONResponse(context, **response_kwargs)
        else:
            return HttpResponseBadRequest()

    def _patch_body_data_to_post(self, request):
        self.request = patch_body_json_data(request)
        return self.request
