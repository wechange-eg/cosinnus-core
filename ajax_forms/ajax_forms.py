import logging

from django.contrib.messages.api import get_messages
from django.http.response import JsonResponse
from django.template.context import make_context
from django.template.loader import render_to_string
from django.utils.encoding import force_text
import copy

logger = logging.getLogger('cosinnus')


class AjaxEnabledFormViewBaseMixin(object):
    
    ajax_form_partial = None # '/path/to/template.html'
    ajax_result_partial = None # '/path/to/template.html'


class AjaxFormsCreateViewMixin(AjaxEnabledFormViewBaseMixin):
    
    """ A mixin for a CreateView that enables POSTing to that view with an
        ajax request, receiving a JsonResponse back. With this you can make
        your existing template form use ajax calls with just a few tweaks,
        without writing new logic.
        
        How to use for any of your Django-Style Forms:
        
        # In the view:
            - include this mixin
            - set the attribute `ajax_form_partial` to a template partial that renders *only*
                the complete <form> with all fields. You may want to refactor your form view template.
            - set the attribute `ajax_result_partial` to a template partial that renders *only*
                the snippet for the result object that was created with the form. This will be 
                added to your page after the ajax form resolves successfully
        
        # In your template:
            - Include the JS script: <script src="{% static 'js/ajax_forms.js' %}"></script>
            - To your <form>, add the attribute data-target="ajax-form"
            - To your <form>, add an id="<unique-form-id>"
            - (optional) To your main template, add an anchor for the result HTML to be appended to:
                <div data-target="ajax-form-result-anchor" data-ajax-form-id="<unique-form-id>"></div>
                (Use data-target="ajax-form-result-anchor-before" to prepend them).
                This anchor must have the same id as the <form>. The objects in this template
                must be referenced by `object` as this is what will be passed in the context.
            - (optional) In your main template, mark elements that will be removed when the ajax
                form resolves by adding the attributes
                `data-target="ajax-form-result-anchor" data-ajax-form-id="<unique-form-id>"`
            - (optional) To your <form> add an attribute with arbitrary JS code to execude
                when the ajax form resolves: `data-ajax-oncomplete="alert('Success!')`
            
    """
    
    def form_valid(self, form):
        if not self.request.is_ajax():
            return super(AjaxFormsCreateViewMixin, self).form_valid(form)
        
        super(AjaxFormsCreateViewMixin, self).form_valid(form)
        
        form_id = self.request.POST.get('ajax_form_id')
        context = make_context({
            'object': self.object,
            'user': self.request.user,
        }, request=self.request).flatten()
        data = {
            'result_html': render_to_string(self.ajax_result_partial, context, request=self.request),
            'new_form_html': self.render_new_form(self.ajax_form_partial, form_id),
            'ajax_form_id': form_id,
            'messages': [force_text(msg) for msg in get_messages(self.request)], # this consumes the messages
        }
        return JsonResponse(data)
    
    def form_invalid(self, form):
        if not self.request.is_ajax():
            return super(AjaxFormsCreateViewMixin, self).form_invalid(form)
        data = {
            'form_errors': form.errors
        }
        return JsonResponse(data, status=400)
    
    def render_new_form(self, template, form_id):
        """ Renders a fresh form using only the `template` partial """
        
        form_class = self.get_form_class()
        form_kwargs = {
            'initial': self.get_initial(),
            'prefix': self.get_prefix(),
        }
        form = form_class(**form_kwargs)
        context = self.get_context_data(form=form) # this skips `self.get_form()` because 'form' is in kwargs 
        context.update({
            'action_url': self.request.get_full_path(),
            'form_id': form_id,
            'user': self.request.user,
        })
        form_html = render_to_string(self.ajax_form_partial, context, self.request)
        return form_html

    
class AjaxFormsCommentCreateViewMixin(AjaxFormsCreateViewMixin):
    """ Can be used for any CommentCreateView in BaseTaggableObjects """
    
    ajax_form_partial = 'cosinnus/v2/dashboard/timeline_item_comment_form.html'
    ajax_result_partial = 'cosinnus/v2/dashboard/timeline_item_comment.html'
    

class AjaxFormsDeleteViewMixin(object):
    
    """ A mixin for a DeleteView that enables POSTing to that view with an
        ajax request, receiving a JsonResponse back. With this you can make
        your existing template form use ajax calls with just a few tweaks,
        without writing new logic.
        
        How to use for any of your Django-Style Forms:
        
        # In the view:
            - include this mixin
        
        # In your template:
            - Include the JS script: <script src="{% static 'js/ajax_forms.js' %}"></script>
            - To your <form>, add the attribute data-target="ajax-form"
            - To your <form>, add an id="<unique-form-id>"
            - To your object template, add these attributes to any element you want to be
                removed when the delete process resolves successfully:
                `data-target="ajax-form-delete-element" data-ajax-form-id="<unique-form-id>"`
                This anchor must have the same id as the <form>. The objects in this template
                must be referenced by `object` as this is what will be passed in the context.
    """
    
    def delete(self, *args, **kwargs):
        if not self.request.is_ajax():
            return super(AjaxFormsDeleteViewMixin, self).delete(*args, **kwargs)
        
        try:
            super(AjaxFormsDeleteViewMixin, self).delete(*args, **kwargs)
            form_id = self.request.POST.get('ajax_form_id')
            data = {
                'ajax_form_id': form_id,
                'messages': [force_text(msg) for msg in get_messages(self.request)], # this consumes the messages
            }
            return JsonResponse(data)
        except:
            raise
        
