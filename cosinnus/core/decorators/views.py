# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import functools

from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponseForbidden, HttpResponseNotFound
from django.utils.decorators import available_attrs
from django.utils.translation import ugettext_lazy as _

from cosinnus.models.group import CosinnusGroup
from cosinnus.utils.permissions import check_ug_admin, check_ug_membership
from django.contrib import messages
from django.http.response import HttpResponseRedirect
from django.core.urlresolvers import reverse_lazy


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
        lambda u: u.is_superuser
    )
    return actual_decorator(function)


def require_admin_access_decorator(group_url_arg='group'):
    def decorator(function):
        @functools.wraps(function, assigned=available_attrs(function))
        def wrapper(request, *args, **kwargs):
            group_name = kwargs.get(group_url_arg, None)
            if not group_name:
                return HttpResponseNotFound(_("No group provided"))

            try:
                group = CosinnusGroup.objects.get(slug=group_name)
            except CosinnusGroup.DoesNotExist:
                return HttpResponseNotFound(_("No group found with this name"))

            user = request.user

            if user.is_superuser or check_ug_admin(user, group):
                kwargs['group'] = group
                return function(request, *args, **kwargs)

            return HttpResponseForbidden(_("Access denied"))
        return wrapper
    return decorator


def require_admin_access(group_url_kwarg='group', group_attr='group'):
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
        @functools.wraps(function, assigned=available_attrs(function))
        def wrapper(self, request, *args, **kwargs):
            group_name = kwargs.get(group_url_kwarg, None)
            if not group_name:
                return HttpResponseNotFound(_("No group provided"))

            try:
                group = CosinnusGroup.objects.get(slug=group_name)
            except CosinnusGroup.DoesNotExist:
                return HttpResponseNotFound(_("No group found with this name"))

            user = request.user

            if user.is_superuser or check_ug_admin(user, group):
                setattr(self, group_attr, group)
                return function(self, request, *args, **kwargs)

            return HttpResponseForbidden(_("Access denied"))
        return wrapper
    return decorator


def require_read_access(group_url_kwarg='group', group_attr='group'):
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
        @functools.wraps(function, assigned=available_attrs(function))
        def wrapper(self, request, *args, **kwargs):
            group_name = kwargs.get(group_url_kwarg, None)
            if not group_name:
                return HttpResponseNotFound(_("No group provided"))

            try:
                group = CosinnusGroup.objects.get(slug=group_name)
            except CosinnusGroup.DoesNotExist:
                return HttpResponseNotFound(_("No group found with this name"))

            user = request.user
            
            if not group.public and not user.is_authenticated():
                messages.error(request, _('Please log in to access this page.'))
                return HttpResponseRedirect(reverse_lazy('login') + '?next=' + request.path)

            if group.public or user.is_superuser or \
                    check_ug_membership(user, group):
                setattr(self, group_attr, group)
                return function(self, request, *args, **kwargs)

            return HttpResponseForbidden(_("Access denied"))
        return wrapper
    return decorator


def require_write_access(group_url_kwarg='group', group_attr='group'):
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
        @functools.wraps(function, assigned=available_attrs(function))
        def wrapper(self, request, *args, **kwargs):
            group_name = kwargs.get(group_url_kwarg, None)
            if not group_name:
                return HttpResponseNotFound(_("No group provided"))

            try:
                group = CosinnusGroup.objects.get(slug=group_name)
            except CosinnusGroup.DoesNotExist:
                return HttpResponseNotFound(_("No group found with this name"))

            user = request.user
            is_member = check_ug_membership(user, group)
            
            if not user.is_authenticated():
                messages.error(request, _('Please log in to access this page.'))
                return HttpResponseRedirect(reverse_lazy('login') + '?next=' + request.path)
                
            if (is_member or user.is_superuser or group.public):
                setattr(self, group_attr, group)
                return function(self, request, *args, **kwargs)

            return HttpResponseForbidden(_("Access denied"))
        return wrapper
    return decorator
