# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import apps
from django.urls import reverse_lazy
from django.views.generic import RedirectView
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _, LANGUAGE_SESSION_KEY

from cosinnus.conf import settings

from cosinnus.utils.context_processors import cosinnus as cosinnus_context
from cosinnus.utils.context_processors import settings as cosinnus_context_settings
from cosinnus.utils.urls import safe_redirect
from django.http.response import  HttpResponseNotFound,\
    HttpResponseForbidden, HttpResponseServerError, HttpResponseNotAllowed,\
    HttpResponseBadRequest, JsonResponse
from django.template.loader import render_to_string
from django.contrib.contenttypes.models import ContentType
from cosinnus.models.tagged import LikeObject
from annoying.functions import get_object_or_None
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.views import LoginView, LogoutView

class IndexView(RedirectView):
    permanent = False
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
    content = render_to_string('cosinnus/common/403.html', _get_bare_cosinnus_context(request), request)
    return HttpResponseForbidden(content)

def view_403_csrf(request, reason=""):
    content = render_to_string('cosinnus/common/403_csrf.html', _get_bare_cosinnus_context(request), request)
    return HttpResponseForbidden(content)

def view_404(request):
    content = render_to_string('cosinnus/common/404.html', _get_bare_cosinnus_context(request), request)
    return HttpResponseNotFound(content)

def view_500(request):
    content = render_to_string('cosinnus/common/500.html')
    return HttpResponseServerError(content)


class SwitchLanguageView(RedirectView):
    
    permanent = False
    
    def get(self, request, *args, **kwargs):
        language = kwargs.pop('language', None)
        
        if not language or language not in list(dict(settings.LANGUAGES).keys()):
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
    response = LoginView.as_view(**kwargs)(request)  #login(request, **kwargs)
    if request.method == 'POST' and request.user.is_authenticated:
        response.set_cookie('wp_user_logged_in', 1, 60*60*24*30) # 30 day expiry
    return response

def cosinnus_logout(request, **kwargs):
    """ Wraps the django logout view to delete the "wp_user_logged_in" cookie on logouts
        (this seems to only clear the value of the cookie and not completely delete it!) """
    response = LogoutView.as_view(**kwargs)(request) # logout(request, **kwargs)
    if not request.user.is_authenticated:
        response.delete_cookie('wp_user_logged_in')
    return response

@csrf_protect
def do_like(request, **kwargs):
    """ Expected POST arguments:
        - ct: django content-type string (expects e.g. 'cosinnus_note.Note')
        - id: Id of the object. (optional if slug is given)
        - slug: Slug of the object (optional if id is given)
        - like: (optional) 0/1, whether to like or unlike
        - follow: (optional) 0/1, whether to follow or unfollow
        
        User needs to be logged in.
        Target object needs to be visible (permissions) to the logged in user.
        If `follow`=1 param is given without `like`, a liked=False,followed=True object will be created.
        If the LikeObject results in being liked=False,followed=False, it will be deleted immediately.
    """
    
    if not request.is_ajax() and not request.method=='POST':
        return HttpResponseNotAllowed('POST', content='This endpoint is for POST only.')
    if not request.user.is_authenticated:
        return HttpResponseForbidden('Not authenticated.')
    
    ct = request.POST.get('ct', None)  # expects 'cosinnus_note.Note'
    obj_id = request.POST.get('id', None)
    slug = request.POST.get('slug', None)
    like = request.POST.get('like', None)
    follow = request.POST.get('follow', None)
    
    if ct is None or (id is None and slug is None) or (like is None and follow is None):
        return HttpResponseBadRequest('Incomplete data submitted.')
    
    app_label, model = ct.split('.')
    model_cls = apps.get_model(app_label, model)
    content_type = ContentType.objects.get_for_model(model_cls)
    
    obj = None
    if obj_id is None and slug:
        obj = get_object_or_None(model_cls, slug=slug)
    else:
        obj = get_object_or_None(model_cls, id=obj_id)
    if obj is None:
        return HttpResponseNotFound('Target object not found on server.')
    
    liked_obj = get_object_or_None(LikeObject, content_type=content_type, object_id=obj.id, user=request.user)
    # unlike and unfollow
    if (like == '0' or like is None) and (follow == '0' or follow is None):
        if liked_obj is None:
            # nothing to do here
            pass
        else:
            liked_obj.delete()
            liked_obj = None
    else:
        if liked_obj is None:
            # initialize an object but don't save it yet
            liked_obj = LikeObject(content_type=content_type, object_id=obj.id, user=request.user, liked=False)
            
        if not like is None:
            liked_obj.liked = like == '1'
        if not follow is None:
            liked_obj.followed =  follow == '1'
            
        liked_obj.save()
        
        # update the liked object's index
        if hasattr(obj, 'update_index'):
            obj.update_index()
    
    return JsonResponse({'liked': liked_obj and liked_obj.liked or False, 'followed': liked_obj and liked_obj.followed or False})
    
    