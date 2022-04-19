# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
import functools

from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden, HttpResponseNotFound
from django.utils.translation import ugettext_lazy as _
from cosinnus.utils.group import get_cosinnus_group_model

from cosinnus_organization.models import CosinnusOrganization
from cosinnus.utils.permissions import check_object_write_access,\
    check_group_create_objects_access, check_object_read_access, get_user_token,\
    check_user_superuser, check_user_verified, check_user_portal_manager
from django.contrib import messages
from django.http.response import HttpResponseRedirect, Http404
from django.urls import reverse_lazy
from django.core.exceptions import PermissionDenied
from cosinnus.core.registries.group_models import group_model_registry
from django.contrib.auth.models import User
from cosinnus.models.tagged import BaseTagObject
from cosinnus.utils.exceptions import CosinnusPermissionDeniedException

import logging
from cosinnus.models.group import CosinnusPortal
from django.shortcuts import redirect, render, get_object_or_404
from cosinnus.utils.urls import group_aware_reverse
from django.template.defaultfilters import urlencode
logger = logging.getLogger('cosinnus')


MSG_USER_NOT_VERIFIED = _('You need to verify your email before you can use this part of the site! Please check your emails and click the link in the verification email you received from us, or request a new email by clicking the link above.')


def redirect_to_error_page(request, view=None, group=None):
    """ Returns a redirect to an error page with the same URL and support for displaying error messages.
        You should always use `messages.error/warning/info` before calling this function, otherwise the page
        will be blank.
        @param group: If supplied, the user will in most cases be redirected to the group's micropage instead """
    # support for the ajaxable view mixin
    if view and getattr(view, 'is_ajax_request_url', False):
        return HttpResponseForbidden('Not authenticated')
    # redirect to group's micropage
    if group is not None:
        # only redirect to micropage if user isn't a member of the group
        if not request.user.is_authenticated or not request.user.id in group.members:
            messages.warning(request, group.trans.MESSAGE_MEMBERS_ONLY)
            return redirect(group_aware_reverse('cosinnus:group-dashboard', kwargs={'group': group}))
    return render(request, template_name='cosinnus/common/error.html', context={})


def redirect_to_403(request, view=None, group=None):
    """ Returns a redirect to a permission-denied page with the same URL and an and an error message 
        @param group: If supplied, the user will in most cases be redirected to the group's micropage instead """
    # support for the ajaxable view mixin
    if view and getattr(view, 'is_ajax_request_url', False):
        return HttpResponseForbidden('Not authenticated')
    # redirect to group's micropage and give permission denied Error message, but not 403
    if group is not None:
        # only redirect to micropage if user isn't a member of the group
        if not request.user.is_authenticated or not request.user.id in group.members:
            messages.warning(request, group.trans.MESSAGE_MEMBERS_ONLY)
            return redirect(group_aware_reverse('cosinnus:group-dashboard', kwargs={'group': group}))
    raise PermissionDenied


def redirect_to_not_logged_in(request, view=None, group=None):
    """ Returns a redirect to the login page with a next-URL parameter and an error message 
        @param group: If supplied, the user will in most cases be redirected to the group's micropage instead """
    # support for the ajaxable view mixin
    if view and getattr(view, 'is_ajax_request_url', False):
        return HttpResponseForbidden('Not authenticated')
    # redirect to group's micropage and give login required error message
    next_arg = request.path
    if request.GET.keys():
        next_arg += '?' + '&'.join(["%s=%s" % (k,v) for k,v in request.GET.items()])
    next_arg = urlencode(next_arg)
    if group is not None:
        messages.warning(request, _('Only registered members can see the content you requested! Log in or create an account now!'))
    else:
        messages.error(request, _('Please log in to access this page.'))
    if group is not None and group.is_publicly_visible:
        return redirect(group_aware_reverse('cosinnus:group-dashboard', kwargs={'group': group}) + '?next=' + next_arg)
    return HttpResponseRedirect(reverse_lazy('login') + '?next=' + next_arg)


def redirect_to_not_verified(request, view=None, group=None):
    """ Returns a redirect to an empty page with an error message, telling the user they need to verify
        their email address to continue. """
    messages.warning(request, MSG_USER_NOT_VERIFIED)
    return redirect_to_error_page(request, view=view, group=group)


def get_group_for_request(group_name, request):
    """ Retrieve the proxy group object depending on the URL path regarding 
        the registered group models.
        A CosinnusGroup will not be returned if it is requested by an URL
        path with a different group_model_key than the one it got registered with. """
    group_url_key = request.path.split('/')[1]
    if group_url_key == 'organizations':
        group_class = CosinnusOrganization
    else:
        group_class = group_model_registry.get(group_url_key, None)
    
    if group_class:
        try:
            # support cross portal tokens on POSTs
            portal_id = int(request.POST.get('cosinnus_cross_portal', CosinnusPortal.get_current().id))
            group = group_class.objects.get(slug=group_name, portal_id=portal_id)
            if type(group) is group_class:
                if group.is_active:
                    return group
                else:
                    logger.warn('Cosinnus.core.decorators: Failed to retrieve group because it is inactive!', 
                     extra={'team_name': group_name, 'url': request.path, 'team_type': type(group), 'group_class': group_class, 'group_slug': group.slug, 'group_pk': group.id, 'refered': request.META.get('HTTP_REFERER', 'N/A')})
            else:
                logger.warn('Cosinnus.core.decorators: Failed to retrieve group because its classes didnt match!', 
                     extra={'team_name': group_name, 'url': request.path, 'team_type': type(group), 'group_class': group_class, 'group_slug': group.slug, 'group_pk': group.id, 'refered': request.META.get('HTTP_REFERER', 'N/A')})
        except group_class.DoesNotExist as e:
            #logger.warn('Cosinnus.core.decorators: Failed to retrieve group! The exception was: "%s"' % str(e), 
            #         extra={'team_name': group_name, 'url': request.path, 'group_class': group_class, 'refered': request.META.get('HTTP_REFERER', 'N/A')})
            # this happens during a regular 404 when users navigate to a group URL that no longer exists
            pass
    else:
        logger.warn('Cosinnus.core.decorators: Failed to retrieve group because no group class was found!',
                     extra={'team_name': group_name, 'url': request.path, 'refered': request.META.get('HTTP_REFERER', 'N/A')})
    
    raise Http404

    

def staff_required(function):
    """A function decorator to assure a requesting user is a staff user."""
    actual_decorator = user_passes_test(
        lambda u: u.is_staff
    )
    return actual_decorator(function)


def superuser_required(function):
    """A function decorator to assure a requesting user has the superuser flag
    """
    actual_decorator = user_passes_test(
        lambda u: check_user_superuser(u)
    )
    return actual_decorator(function)

def membership_required(function):
    """A function decorator to assure a requesting user is an authenticated member
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated
    )
    return actual_decorator(function)


def _check_deactivated_app_access(view, group, request):
    """ Will check if a view is being accessed within a cosinnus app that 
    has been deactivated for this group. """
    app_name = view.__module__.split('.')[0]
    if hasattr(group, 'is_app_deactivated') and group.is_app_deactivated(app_name) \
            and not getattr(view, 'ALLOW_VIEW_ACCESS_WHEN_GROUP_APP_DEACTIVATED', False):
        messages.error(request, _("The page you tried to access belongs to an app that has been deactivated for this %(team_type)s. If you feel this is in error, ask the %(team_type)s's administrator to reactivate the app.") % {'team_type': group._meta.verbose_name})
        return HttpResponseRedirect(group.get_absolute_url())
    return None


def require_admin_access_decorator(group_url_arg='group'):
    def decorator(function):
        @functools.wraps(function)
        def wrapper(request, *args, **kwargs):
            group_name = kwargs.get(group_url_arg, None)
            if not group_name:
                return HttpResponseNotFound(_("No team provided"))

            group = get_group_for_request(group_name, request)
            user = request.user

            if not user.is_authenticated:
                return redirect_to_not_logged_in(request, view=self, group=group)

            if check_object_write_access(group, user):
                kwargs['group'] = group
                return function(request, *args, **kwargs)

            # Access denied, redirect to 403 page and and display an error message
            return redirect_to_403(request, self, group=group)
            
        return wrapper
    return decorator


def require_logged_in():
    """A method decorator that checks that the requesting user is logged in
    """

    def decorator(function):
        @functools.wraps(function)
        def wrapper(self, request, *args, **kwargs):
            user = request.user
            
            if not user.is_authenticated:
                return redirect_to_not_logged_in(request, view=self)
            
            return function(self, request, *args, **kwargs)
            
        return wrapper
    return decorator


def require_verified_user_access():
    """A method decorator that checks that the requesting user has a verified email address  """

    def decorator(function):
        @functools.wraps(function)
        def wrapper(self, request, *args, **kwargs):
            user = request.user
            if not user.is_authenticated:
                return redirect_to_not_logged_in(request, view=self)
            if not check_user_verified(user):
                return redirect_to_not_verified(request, view=self)
            
            return function(self, request, *args, **kwargs)
            
        return wrapper
    return decorator


def require_superuser():
    """A method decorator that checks that the requesting user is a superuser (admin or portal admin)
    """

    def decorator(function):
        @functools.wraps(function)
        def wrapper(self, request, *args, **kwargs):
            user = request.user
            
            if not user.is_authenticated:
                return redirect_to_not_logged_in(request, view=self)
            if not check_user_superuser(user):
                raise PermissionDenied('You do not have permission to access this page.')
            
            return function(self, request, *args, **kwargs)
            
        return wrapper
    return decorator


def require_portal_manager():
    """A method decorator that checks that the requesting user is a portal manager or superuser (admin or portal admin)
    """

    def decorator(function):
        @functools.wraps(function)
        def wrapper(self, request, *args, **kwargs):
            user = request.user
            
            if not user.is_authenticated:
                return redirect_to_not_logged_in(request, view=self)
            if not check_user_portal_manager(user) and not check_user_superuser(user):
                raise PermissionDenied('You do not have permission to access this page.')
            
            return function(self, request, *args, **kwargs)
            
        return wrapper
    return decorator


def dispatch_group_access(group_url_kwarg='group', group_attr='group'):
    """A method decorator that takes the group name from the kwargs of a
    dispatch function in CBVs and performs no priviledge checks

    Additionally this function populates the group instance to the view
    instance as attribute `group_attr`

    :param str group_url_kwarg: The name of the key containing the group name.
        Defaults to `'group'`.
    :param str group_attr: The attribute name which can later be used to access
        the group from within an view instance (e.g. `self.group`). Defaults to
        `'group'`.
    """

    def decorator(function):
        @functools.wraps(function)
        def wrapper(self, request, *args, **kwargs):
            group_name = kwargs.get(group_url_kwarg, None)
            if not group_name:
                return HttpResponseNotFound(_("No team provided"))

            group = get_group_for_request(group_name, request)
            
            deactivated_app_error = _check_deactivated_app_access(self, group, request)
            if deactivated_app_error:
                return deactivated_app_error

            setattr(self, group_attr, group)
            return function(self, request, *args, **kwargs)

            
        return wrapper
    return decorator


def require_admin_access(group_url_kwarg=None, group_attr=None):
    """A method decorator that takes the group name from the kwargs of a
    dispatch function in CBVs and checks that the requesting user is allowed to
    perform administrative operations.

    Additionally this function populates the group instance to the view
    instance as attribute `group_attr`

    :param str group_url_kwarg: The name of the key containing the group name.
        Defaults to `'group'`.
    :param str group_attr: The attribute name which can later be used to access
        the group from within an view instance (e.g. `self.group`). Defaults to
        `'group'`.
    """

    def decorator(function):
        @functools.wraps(function)
        def wrapper(self, request, *args, **kwargs):
            url_kwarg = group_url_kwarg or getattr(self, 'group_url_kwarg', 'group')
            attr = group_attr or getattr(self, 'group_attr', 'group')
            group_name = kwargs.get(url_kwarg, None)
            if not group_name:
                return HttpResponseNotFound(_("No team provided"))

            group = get_group_for_request(group_name, request)
            user = request.user
            
            deactivated_app_error = _check_deactivated_app_access(self, group, request)
            if deactivated_app_error:
                return deactivated_app_error
            
            if not user.is_authenticated:
                return redirect_to_not_logged_in(request, view=self, group=group)

            if check_object_write_access(group, user):
                setattr(self, attr, group)
                return function(self, request, *args, **kwargs)

            # Access denied, redirect to 403 page and and display an error message
            return redirect_to_403(request, self, group=group)
            
        return wrapper
    return decorator


def require_read_access(group_url_kwarg=None, group_attr=None):
    """A method decorator that takes the group name from the kwargs of a
    dispatch function in CBVs and checks that the requesting user is allowed to
    perform read operations.

    Additionally this function populates the group instance to the view
    instance as attribute `group_attr`

    :param str group_url_kwarg: The name of the key containing the group name.
        Defaults to `'group'`.
    :param str group_attr: The attribute name which can later be used to access
        the group from within an view instance (e.g. `self.group`). Defaults to
        `'group'`.
    """

    def decorator(function):
        @functools.wraps(function)
        def wrapper(self, request, *args, **kwargs):
            url_kwarg = group_url_kwarg or getattr(self, 'group_url_kwarg', 'group')
            attr = group_attr or getattr(self, 'group_attr', 'group')
            group_name = kwargs.get(url_kwarg, None)
            if not group_name:
                return HttpResponseNotFound(_("No team provided"))
            group = get_group_for_request(group_name, request)
            user = request.user

            # this is why almost every BaseTaggableObject's View has a .group attribute:
            setattr(self, attr, group)
            
            # record visit to group for this user
            if user.is_authenticated and hasattr(group, 'mark_visited'):
                group.mark_visited(user)
            
            requested_object = None
            try:
                requested_object = self.get_object()
            except (AttributeError, TypeError):
                pass
            except CosinnusPermissionDeniedException:
                if not user.is_authenticated:
                    return redirect_to_not_logged_in(request, view=self, group=group)
                else:
                    return redirect_to_403(request, self, group=group)
            
            obj_public = requested_object and getattr(requested_object, 'media_tag', None) \
                    and requested_object.media_tag.visibility == BaseTagObject.VISIBILITY_ALL
            # catch anyonymous users trying to navigate to private groups (else self.get_object() throws a Http404!)
            if not (obj_public or group.public or user.is_authenticated):
                return redirect_to_not_logged_in(request, view=self, group=group)
            
            deactivated_app_error = _check_deactivated_app_access(self, group, request)
            if deactivated_app_error:
                return deactivated_app_error
            
            if requested_object:
                if check_object_read_access(requested_object, user):
                    return function(self, request, *args, **kwargs)
            else:
                if check_object_read_access(group, user):
                    return function(self, request, *args, **kwargs)

            # Access denied, redirect to 403 page and and display an error message
            return redirect_to_403(request, self, group=group)
            
        return wrapper
    return decorator


def require_write_access(group_url_kwarg=None, group_attr=None):
    """A method decorator that takes the group name from the kwargs of a
    dispatch function in CBVs and checks that the requesting user is allowed to
    perform write operations.

    Additionally this function populates the group instance to the view
    instance as attribute `group_attr`

    :param str group_url_kwarg: The name of the key containing the group name.
        Defaults to `'group'`.
    :param str group_attr: The attribute name which can later be used to access
        the group from within an view instance (e.g. `self.group`). Defaults to
        `'group'`.
    """

    def decorator(function):
        @functools.wraps(function)
        def wrapper(self, request, *args, **kwargs):
            url_kwarg = group_url_kwarg or getattr(self, 'group_url_kwarg', 'group')
            attr = group_attr or getattr(self, 'group_attr', 'group')
            group_name = kwargs.get(url_kwarg, None)
            if not group_name:
                return HttpResponseNotFound(_("No team provided"))
            
            group = get_group_for_request(group_name, request)
            user = request.user
            
            # set the group attr    
            setattr(self, attr, group)
            
            # catch anyonymous users trying to naviagte to private groups (else self.get_object() throws a Http404!)
            if not group.public and not user.is_authenticated:
                return redirect_to_not_logged_in(request, view=self, group=group)
            
            deactivated_app_error = _check_deactivated_app_access(self, group, request)
            if deactivated_app_error:
                return deactivated_app_error
            
            requested_object = None
            try:
                requested_object = self.get_object()
            except (AttributeError, TypeError):
                pass
            
            # objects can never be written by non-logged in members
            if not user.is_authenticated:
                return redirect_to_not_logged_in(request, view=self, group=group)
            
            if requested_object:
                # editing/deleting an object, check if we are owner or staff member or group admin or site admin
                if check_object_write_access(requested_object, user):
                    return function(self, request, *args, **kwargs)
            else:
                # creating a new object, check if we can create objects in the group
                if check_group_create_objects_access(group, user):
                    return function(self, request, *args, **kwargs)
            
            # Access denied, redirect to 403 page and and display an error message
            return redirect_to_403(request, self, group=group)
            
        return wrapper
    return decorator


def require_write_access_groupless():
    """A method decorator that takes the requested object of i.e. an edit or delete view in the
    dispatch function and checks that the requesting user is allowed to
    perform write operations.
    """

    def decorator(function):
        @functools.wraps(function)
        def wrapper(self, request, *args, **kwargs):
            user = request.user
            
            # catch anyonymous users trying to naviagte here
            if not user.is_authenticated:
                return redirect_to_not_logged_in(request, view=self)
            
            requested_object = None
            try:
                requested_object = self.get_object()
            except (AttributeError, TypeError):
                pass
            
            if requested_object:
                # editing/deleting an object, check if we are owner or staff member or group admin or site admin
                if check_object_write_access(requested_object, user):
                    return function(self, request, *args, **kwargs)

            # Access denied, redirect to 403 page and and display an error message
            return redirect_to_403(request, self)
            
        return wrapper
    return decorator



def require_user_token_access(token_name, group_url_kwarg='group', group_attr='group', id_url_kwarg=None):
    """ A method decorator that allows access only if the URL params
    `user=999&token=1234567` are supplied, and if the token supplied matches
    the specific token (determined by :param ``token_name``) in the supplied 
    user's settings. Please only use different token_names for each specific purpose.
        
    Additionally this function populates the group instance to the view
    instance as attribute `group_attr` and the resolved token user as attribute `user`

    :param str group_url_kwarg: The name of the key containing the group name.
        Defaults to `'group'`.
    :param str group_attr: The attribute name which can later be used to access
        the group from within an view instance (e.g. `self.group`). Defaults to
        `'group'`.
    :param str id_url_kwarg: The attribut id which can later be used to access
        the group or a project from within an view instance (e.g. `team_id`). Defaults to
        `None`.
    """

    def decorator(function):
        @functools.wraps(function)
        def wrapper(self, request, *args, **kwargs):
            
            # assume no user is logged in, and check the user id and token from the args
            user_id = request.GET.get('user', None)
            token = request.GET.get('token', None)
            if not user_id or not token:
                return HttpResponseForbidden('No authentication supplied!')
            
            user = None
            user_token = None
            try:
                user = User.objects.get(id=user_id)
                user_token = get_user_token(user, token_name)
            except User.DoesNotExist:
                pass
            if not user or not user_token or not user_token == token:
                return HttpResponseForbidden('Authentication invalid!')
            
            self.user = user
            
            group_name = kwargs.get(group_url_kwarg, None)
            if id_url_kwarg is not None:
                team_id = kwargs.get(id_url_kwarg)
                group = get_object_or_404(get_cosinnus_group_model(), id=team_id, portal_id=CosinnusPortal.get_current().id)
            elif not group_name:
                return HttpResponseNotFound(_("No team provided"))
            else:
                group = get_group_for_request(group_name, request)

            
            # set the group attribute
            setattr(self, group_attr, group)
            
            deactivated_app_error = _check_deactivated_app_access(self, group, request)
            if deactivated_app_error:
                return deactivated_app_error
            
            requested_object = None
            try:
                requested_object = self.get_object()
            except (AttributeError, TypeError):
                pass
            
            if requested_object:
                if check_object_read_access(requested_object, user):
                    return function(self, request, *args, **kwargs)
            else:
                if check_object_read_access(group, user):
                    return function(self, request, *args, **kwargs)

            # Access denied, redirect to 403 page and and display an error message
            return redirect_to_403(request, self, group=group)
            
        return wrapper
    return decorator


def require_create_objects_in_access(group_url_kwarg='group', group_attr='group'):
    """A method decorator that takes the group name from the kwargs of a
    dispatch function in CBVs and checks that the requesting user is allowed to
    perform read operations.

    Additionally this function populates the group instance to the view
    instance as attribute `group_attr`

    :param str group_url_kwarg: The name of the key containing the group name.
        Defaults to `'group'`.
    :param str group_attr: The attribute name which can later be used to access
        the group from within an view instance (e.g. `self.group`). Defaults to
        `'group'`.
    """

    def decorator(function):
        @functools.wraps(function)
        def wrapper(self, request, *args, **kwargs):
            group_name = kwargs.get(group_url_kwarg, None)
            if not group_name:
                return HttpResponseNotFound(_("No team provided"))

            group = get_group_for_request(group_name, request)
            user = request.user
            
            # set the group attribute
            setattr(self, group_attr, group)
            
            if not group.public and not user.is_authenticated:
                return redirect_to_not_logged_in(request, view=self, group=group)
            
            deactivated_app_error = _check_deactivated_app_access(self, group, request)
            if deactivated_app_error:
                return deactivated_app_error
            
            if check_group_create_objects_access(group, user):
                return function(self, request, *args, **kwargs)

            # Access denied, redirect to 403 page and and display an error message
            return redirect_to_403(request, self, group=group)
            
        return wrapper
    return decorator

