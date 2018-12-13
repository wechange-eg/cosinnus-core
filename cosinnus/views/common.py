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
from cosinnus.views.mixins.group import RequireCreateObjectsInMixin
from django.views.generic.base import View
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import get_object_or_404
from cosinnus.utils.permissions import check_object_write_access,\
    check_object_likefollow_access

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


def view_403(request, exception):
    content = render_to_string('cosinnus/common/403.html', _get_bare_cosinnus_context(request), request)
    return HttpResponseForbidden(content)

def view_403_csrf(request, reason=""):
    content = render_to_string('cosinnus/common/403_csrf.html', _get_bare_cosinnus_context(request), request)
    return HttpResponseForbidden(content)

def view_404(request, exception):
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


UNSPECIFIED = object()

def apply_likefollow_object(obj, user, like=UNSPECIFIED, follow=UNSPECIFIED):
    """
        Toggles the like or follow, or both states on a LikeObject.
        If no LikeObject existed, and either like or follow is True, create a new object.
        If a LikeObject existed, and either like or follow is True, change the existing object.
        If a LikeObject existed, and either like is False, and the model has the `NO_FOLLOW_WITHOUT_LIKE`
            property, delete the existing object.
        If a LikeObject existed, and both like and follow are False, delete the existing object. 
    """
    model_cls = obj._meta.model
    delete_if_unlike = getattr(model_cls, 'NO_FOLLOW_WITHOUT_LIKE', False)
    auto_follow = getattr(model_cls, 'AUTO_FOLLOW_ON_LIKE', False)
    
    content_type = ContentType.objects.get_for_model(model_cls)
    liked_obj = get_object_or_None(LikeObject, content_type=content_type, object_id=obj.id, user=user)
    if (not like or like is UNSPECIFIED) and (not follow or follow is UNSPECIFIED) and liked_obj is None:
        # only unlike or unfollow or both, and no object: nothing to do here
        pass
    elif not (like is UNSPECIFIED and follow is UNSPECIFIED):
        if liked_obj is None:
            # initialize an object but don't save it yet
            liked_obj = LikeObject(content_type=content_type, object_id=obj.id, user=user, liked=False, followed=auto_follow)
        # apply properties
        if not like is UNSPECIFIED:
            liked_obj.liked = like
        if not follow is UNSPECIFIED:
            liked_obj.followed = follow
        # check for deletion state
        if not liked_obj.liked and (not liked_obj.followed or delete_if_unlike):
            liked_obj.delete()
            liked_obj = None
        else:
            liked_obj.save()
        
        # delete the objects like/folow cache
        obj.clear_likes_cache()
        # update the liked object's index
        if hasattr(obj, 'update_index'):
            obj.update_index()
    
    was_liked = liked_obj and liked_obj.liked or False
    was_followed = liked_obj and liked_obj.followed or False
    return was_liked, was_followed


def apply_like_object(obj, user, like):
    # create, change or delete the LikeObj, but take care that the FOLLOW is false before deleting
    return apply_likefollow_object(obj, user, like=like, follow=UNSPECIFIED)

def apply_follow_object(obj, user, follow):
    # create, change or delete the LikeObj, but take care that the LIKE is false before deleting
    return apply_likefollow_object(obj, user, like=UNSPECIFIED, follow=follow)


@csrf_protect
def do_likefollow(request, **kwargs):
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
        Special for likefollow combined:
            If the LikeObject results in being liked=False, no matter the follow state, it will be deleted immediately
    """
    
    if not request.is_ajax() and not request.method=='POST':
        return HttpResponseNotAllowed('POST', content='This endpoint is for POST only.')
    if not request.user.is_authenticated:
        return HttpResponseForbidden('Not authenticated.')
    
    PARAM_VALUE_MAP = {
        '1': True,
        '0': False,
        1: True,
        0: False,
    }
    ct = request.POST.get('ct', None)  # expects 'cosinnus_note.Note'
    obj_id = request.POST.get('id', None)
    slug = request.POST.get('slug', None)
    like = PARAM_VALUE_MAP.get(request.POST.get('like', None), UNSPECIFIED)
    follow = PARAM_VALUE_MAP.get(request.POST.get('follow', None), UNSPECIFIED)
    
    if ct is None or (id is None and slug is None) or (like is UNSPECIFIED and follow is UNSPECIFIED):
        return HttpResponseBadRequest('Incomplete data submitted.')
    
    app_label, model = ct.split('.')
    model_cls = apps.get_model(app_label, model)
    
    obj = None
    if obj_id is None and slug:
        obj = get_object_or_None(model_cls, slug=slug)
    else:
        obj = get_object_or_None(model_cls, id=obj_id)
    if obj is None:
        return HttpResponseNotFound('Target object not found on server.')
    
    if not check_object_likefollow_access(obj, request.user):
        return HttpResponseForbidden('Your access to this object is forbidden.')
    
    was_liked, was_followed = apply_likefollow_object(obj, request.user, like=like, follow=follow)
    
    return JsonResponse({'liked': was_liked, 'followed': was_followed})
    

class DeleteElementView(RequireCreateObjectsInMixin, View):
    """ Deletes one or more instances of BaseTaggableObject. Will check write permissions for
        each individual object.
        
        This is a pseudo-abstract class, superclass this with your own view for each cosinnus app.
        Requires `model` to be set to a non-abstract HierarchicalBaseTaggableObject model.
        Expects to find a `group` kwarg.
        Excpects `element_ids[]` as POST arguments.
     """
    
    http_method_names = ['post', ]
    
    model = None
    
    def post(self, request, *args, **kwargs):
        if not self.model:
            raise ImproperlyConfigured('No model class is set for the pseudo-abstract view DeleteElementView.')
        
        element_ids = request.POST.getlist('element_ids[]', [])
        if not (element_ids or self.group):
            return HttpResponseBadRequest('Missing POST fields for this request.')
        
        successful_ids = []
        for element_id in element_ids:
            element = get_object_or_None(self.model, id=element_id, group=self.group)
            
            # check write permission on element
            if not check_object_write_access(element, request.user):
                continue
            if self.delete_element(element):
                successful_ids.append(element_id)
        
        data = {
            'had_errors': len(successful_ids) != len(element_ids),
            'successful_ids': successful_ids,
        }
        return JsonResponse(data)
        
        
    def delete_element(self, element):
        element.delete()
        return True
        
