# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.core.decorators.views import (require_read_access,
    require_write_access, require_admin_access,
    require_create_objects_in_access)
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user
from cosinnus.models.tagged import BaseTaggableObjectModel
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.shortcuts import redirect


class RequireAdminMixin(object):
    """
    Mixing to ease the use of :meth:`require_admin_access`.

    .. seealso:: :class:`RequireReadMixin`, :class:`RequireWriteMixin`, :class:`RequireCreateObjectsInMixin`
    """

    @require_admin_access()
    def dispatch(self, request, *args, **kwargs):
        return super(RequireAdminMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(RequireAdminMixin, self).get_context_data(**kwargs)
        context.update({'group': self.group})
        return context


class RequireReadMixin(object):
    """
    Mixing to ease the use of :meth:`require_read_access`.

    .. seealso:: :class:`RequireAdminMixin`, :class:`RequireWriteMixin`, :class:`RequireCreateObjectsInMixin`
    """

    @require_read_access()
    def dispatch(self, request, *args, **kwargs):
        return super(RequireReadMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(RequireReadMixin, self).get_context_data(**kwargs)
        context.update({'group': self.group})
        return context
    
    def get_queryset(self, **kwargs):
        """ Filter queryset for items which can be accessed by the user given their
            visibility tags
        """
        qs = super(RequireReadMixin, self).get_queryset(**kwargs)
        
        # only use this filter on querysets of media_tagged models
        # alternatively, we could check if qs.model is CosinnusGroup or BaseTaggableObjectModel subclass, 
        # or BaseUserProfileModel subclass, but this is more elegant:
        if hasattr(qs.model, 'media_tag'):
            qs = filter_tagged_object_queryset_for_user(qs, self.request.user)
        
        # very important to set self.queryset to avoid redundant re-filters
        self.queryset = qs
        return qs
    
    
class RequireReadOrRedirectMixin(RequireReadMixin):
    """ Works exactly as :class:`RequireReadMixin`, but offers additional actions when
        the permission requirements are not met.
        
        Set `on_eror_redirect_url` to an URL to redirect to on unmet permissions,
        or override :meth:`on_error` to handle custom behaviour.
         """ 
    
    on_error_redirect_url = None
    
    def dispatch(self, request, *args, **kwargs):
        try:
            forbidden_error = self.check_read(request, *args, **kwargs)
        except PermissionDenied:
            return self.on_error(request, *args, **kwargs)
        if forbidden_error:
            return self.on_error(request, *args, **kwargs)
        return super(RequireReadMixin, self).dispatch(request, *args, **kwargs)
    
    @require_read_access()
    def check_read(self, request, *args, **kwargs):
        return None
    
    def on_error(self, request, *args, **kwargs):
        redirect_url = self.on_error_redirect_url
        if not redirect_url:
            raise ImproperlyConfigured('RequireReadOrRedirectMixin requires "on_error_redirect_url" to be set in the class.')
        return redirect(redirect_url)


class RequireWriteMixin(object):
    """
    Mixing to ease the use of :meth:`require_write_access`.

    .. seealso:: :class:`RequireAdminMixin`, :class:`RequireReadMixin`, :class:`RequireCreateObjectsInMixin`
    """

    @require_write_access()
    def dispatch(self, request, *args, **kwargs):
        return super(RequireWriteMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(RequireWriteMixin, self).get_context_data(**kwargs)
        context.update({'group': self.group})
        return context
    
    
class RequireCreateObjectsInMixin(object):
    """
    Mixing to ease the use of :meth:`require_create_objects_in_access`.

    .. seealso:: :class:`RequireAdminMixin`, :class:`RequireReadMixin`, :class:`RequireWriteMixin`
    """

    @require_create_objects_in_access()
    def dispatch(self, request, *args, **kwargs):
        return super(RequireCreateObjectsInMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(RequireCreateObjectsInMixin, self).get_context_data(**kwargs)
        context.update({'group': self.group})
        return context


class FilterGroupMixin(object):
    """Filters the underlying queryset so that only models referring to the
    given group are returned.
    Also uses select_related on some of the BaseTaggableObjectModel's attributes
    """

    #: See `group_attr` of :py:func:`require_read_access` and similar for usage
    group_attr = 'group'
    #: The actual filter keyword used in the queryset's `filter` function
    group_field = 'group'

    def get_queryset(self, **kwargs):
        fkwargs = {self.get_group_field(): self.get_group_attr()}

        select_related = set(kwargs.pop('select_related', ()))
        select_related.add(self.get_group_field())
        
        qs = super(FilterGroupMixin, self).get_queryset()
        if BaseTaggableObjectModel in qs.model.__bases__:
            select_related.add('creator__cosinnus_profile')
            select_related.add('media_tag')
        
        return qs \
            .filter(**fkwargs) \
            .select_related(*select_related)

    def get_group_attr(self):
        return getattr(self, self.group_attr)

    def get_group_field(self):
        return self.group_field


class GroupFormKwargsMixin(object):
    """
    Works nicely together with :class:`cosinnus.forms.GroupKwargModelFormMixin`
    """
    def get_form_kwargs(self):
        kwargs = super(GroupFormKwargsMixin, self).get_form_kwargs()
        kwargs['group'] = self.group
        return kwargs
