# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from annoying.functions import get_object_or_None
from bs4 import BeautifulSoup
from django.apps import apps
from django.contrib.auth import get_user_model, logout
from django.contrib import messages
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.http.response import  HttpResponseNotFound, \
    HttpResponseForbidden, HttpResponseServerError, HttpResponseNotAllowed, \
    HttpResponseBadRequest, JsonResponse, HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _, LANGUAGE_SESSION_KEY
from django.views.decorators.csrf import csrf_protect
from django.views.generic import RedirectView
from django.views.generic.base import View, TemplateView
import requests

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.tagged import LikeObject
from cosinnus.utils.context_processors import cosinnus as cosinnus_context
from cosinnus.utils.context_processors import settings as cosinnus_context_settings
from cosinnus.utils.permissions import check_object_write_access, \
    check_object_likefollowstar_access
from cosinnus.utils.urls import safe_redirect
from cosinnus.views.mixins.group import RequireCreateObjectsInMixin
from django.shortcuts import redirect
from cosinnus.views.user import send_user_email_to_verify


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


class GenericErrorPageView(TemplateView):
    """ Displays a simple error page, listing all attributed supplied as GET param. """
    
    template_name = 'cosinnus/conference/error_page.html'

generic_error_page_view = GenericErrorPageView.as_view()


class SwitchLanguageView(RedirectView):

    permanent = False

    def get(self, request, *args, **kwargs):
        language = kwargs.pop('language', None)

        if not language or language not in list(dict(settings.LANGUAGES).keys()):
            messages.error(request, _('The language "%s" is not supported' % language))
        else:
            response = super(SwitchLanguageView, self).get(request, *args, **kwargs)
            response.set_cookie(
                settings.LANGUAGE_COOKIE_NAME,
                language,
                max_age=settings.LANGUAGE_COOKIE_AGE,
                path=settings.LANGUAGE_COOKIE_PATH,
                domain=settings.LANGUAGE_COOKIE_DOMAIN,
                secure=settings.LANGUAGE_COOKIE_SECURE,
                httponly=settings.LANGUAGE_COOKIE_HTTPONLY,
                samesite=settings.LANGUAGE_COOKIE_SAMESITE,
            )
        return response

    def get_redirect_url(self, **kwargs):
        return safe_redirect(self.request.GET.get('next', self.request.META.get('HTTP_REFERER', '/')), self.request)


switch_language = SwitchLanguageView.as_view()


def cosinnus_login(request, **kwargs):
    """ Wraps the django login view to set the "wp_user_logged_in" cookie on logins """
    
    # use the sso login form on SSO redirect-logins
    if getattr(settings, 'COSINNUS_IS_OAUTH_PROVIDER', False) \
            and request.GET.get('next', '').startswith('/o/authorize/'):
        kwargs['template_name'] = 'cosinnus/registration/login_sso_provider.html'
    
    response = LoginView.as_view(**kwargs)(request)  #login(request, **kwargs)
    
    if request.method == 'POST' and request.user.is_authenticated:
        # for email-verified-locked portals, "belatedly" refuse the login for users who haven't got their email verified
        if settings.COSINNUS_USER_SIGNUP_FORCE_EMAIL_VERIFIED_BEFORE_LOGIN \
                and CosinnusPortal.get_current().email_needs_verification and not request.user.cosinnus_profile.email_verified:
            # send user another verification email
            send_user_email_to_verify(request.user, request.user.email, request)
            msg = _('New verification email sent!')
            msg += '\n\n' + _('You need to verify your email before logging in. We have just sent you an email with a verifcation link. Please check your inbox, and if you haven\'t received an email, please check your spam folder.')
            msg += '\n\n' + _('We have just now sent another email with a new verification link to you. If the email still has not arrived, you may log in again to receive yet another new email.')
            messages.warning(request, msg)
            logout(request)
            return redirect('login')
        
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

def apply_likefollowstar_object(obj, user, like=UNSPECIFIED, follow=UNSPECIFIED, star=UNSPECIFIED):
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

    if ((not like or like is UNSPECIFIED) and
        (not follow or follow is UNSPECIFIED) and
        (not star or star is UNSPECIFIED) and liked_obj is None):
        # only unlike or unfollow or both, and no object: nothing to do here
        pass
    elif not (like is UNSPECIFIED and follow is UNSPECIFIED and star is UNSPECIFIED):
        if liked_obj is None:
            # initialize an object but don't save it yet
            liked_obj = LikeObject(content_type=content_type, object_id=obj.id, user=user, liked=False, followed=auto_follow)
        # apply properties
        if not like is UNSPECIFIED:
            liked_obj.liked = like
        if not follow is UNSPECIFIED:
            liked_obj.followed = follow
        if not star is UNSPECIFIED:
            liked_obj.starred = star
        # check for deletion state
        if not liked_obj.liked and (not liked_obj.followed or delete_if_unlike) and not liked_obj.starred:
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
    was_stared = liked_obj and liked_obj.starred or False
    return was_liked, was_followed, was_stared


def apply_like_object(obj, user, like):
    # create, change or delete the LikeObj, but take care that the FOLLOW is false before deleting
    return apply_likefollowstar_object(obj, user, like=like, follow=UNSPECIFIED)

def apply_follow_object(obj, user, follow):
    # create, change or delete the LikeObj, but take care that the LIKE is false before deleting
    return apply_likefollowstar_object(obj, user, like=UNSPECIFIED, follow=follow)


@csrf_protect
def do_likefollowstar(request, **kwargs):

    """ Expected POST arguments:
        - ct: django content-type string (expects e.g. 'cosinnus_note.Note')
        - id: Id of the object. (optional if slug is given)
        - slug: Slug of the object (optional if id is given)
        - like: (optional) 0/1, whether to like or unlike
        - follow: (optional) 0/1, whether to follow or unfollow
        - star: (optional) 0/1, whether to star or unstar
        
        User needs to be logged in.
        Target object needs to be visible (permissions) to the logged in user.
        If `follow`=1 param is given without `like`, a liked=False,followed=True object will be created.
        If the LikeObject results in being liked=False,followed=False, it will be deleted immediately.
        Special for likefollowstar combined:
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
    star = PARAM_VALUE_MAP.get(request.POST.get('star', None), UNSPECIFIED)
    # all_deselect indicates the user only wants to unfollow/unstar/unlike
    all_deselect = all([param in (False, UNSPECIFIED,) for param in (like, follow, star,)])
    
    if ct is None or (id is None and slug is None) or (like is UNSPECIFIED and follow is UNSPECIFIED and star is UNSPECIFIED):
        return HttpResponseBadRequest('Incomplete data submitted.')
    
    model_cls = None
    if ct == 'people':
        model_cls = get_user_model()
    else:
        app_label, model = ct.split('.')
        model_cls = apps.get_model(app_label, model)
    
    obj = None
    if not ct == 'people':
        if obj_id is None and slug and '*' in slug:
            # the map api may provide a slug argument in the form of "forum*tolles-event".
            # in this case, the object belongs to a group and needs both slugs to be identified
            group_slug, obj_slug = slug.split('*', 1)
            obj = get_object_or_None(model_cls, slug=obj_slug, group__slug=group_slug, group__portal=CosinnusPortal.get_current())
        elif obj_id is None and slug:
            obj = get_object_or_None(model_cls, slug=slug, portal=CosinnusPortal.get_current())
        else:
            obj = get_object_or_None(model_cls, id=obj_id)
    else:
        user = model_cls.objects.get(username=slug)
        obj = user.cosinnus_profile

    if obj is None:
        return HttpResponseNotFound('Target object not found on server.')
    
    # unfollow/unstar/unlike is always allowed, even if the user's permissions changed
    if not all_deselect and not check_object_likefollowstar_access(obj, request.user):
        return HttpResponseForbidden('Your access to this object is forbidden.')
    
    was_liked, was_followed, was_starred = apply_likefollowstar_object(obj, request.user, like=like, follow=follow, star=star)
    
    return JsonResponse({'liked': was_liked, 'followed': was_followed, 'starred': was_starred})
    

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
    
    
def get_metadata_from_url(request):
    """ Fetches the title and description meta tags from any given url.
        Returns {
            'title': str,
            'description': str,
            <'error': str> (if an error occured),
        } """
        
    if not request.user.is_authenticated:
        return HttpResponseForbidden('Not authenticated')
    
    url = request.GET.get('url', None)
    if not url:
        return HttpResponseBadRequest('Parameter "url" missing!')
    
    error = None
    try:
        response = requests.get(url)
    except:
        error = 'Error fetching URL'
    
    title = ''
    description = ''
    if not error:
        soup = BeautifulSoup(response.text)
        if soup.title:
            title = soup.title.string
        else:
            titletag = soup.find('meta', attrs={'name': 'title'}) 
            if titletag:
                title = titletag.attrs.get('content', '')
            else:
                titletag = soup.find('meta', attrs={'property': 'og:title'}) 
                if titletag:
                    title = titletag.attrs.get('content', '')
        descriptiontag = soup.find('meta', attrs={'name': 'description'}) 
        if descriptiontag:
            description = descriptiontag.attrs.get('content', '')
        else:
            descriptiontag = soup.find('meta', attrs={'property': 'og:description'}) 
            if descriptiontag:
                description = descriptiontag.attrs.get('content', '')
    
    data = {
        'title': title,
        'description': description,
    }
    if error:
        data['error'] = error
    return JsonResponse(data)
    

def empty_file_download(request, **kwargs):
    """ Serves an empty file with the filename given as `COSINNUS_EMPTY_FILE_DOWNLOAD_NAME`.
        Can be used to quickly make a file available for a DNS server check, e.g. for Mailjet. """
    response = HttpResponse('', content_type="application/text")
    response['Content-Disposition'] = 'attachment; filename="%s"' % settings.COSINNUS_EMPTY_FILE_DOWNLOAD_NAME
    return response

        
