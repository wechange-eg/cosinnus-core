# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from cosinnus.core.decorators.views import (require_read_access,
    require_write_access, require_admin_access,
    require_create_objects_in_access, redirect_to_not_logged_in,
    dispatch_group_access, require_logged_in, require_write_access_groupless, 
    require_superuser, require_verified_user_access, require_portal_manager)
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user,\
    check_object_write_access, check_object_read_access
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.models.tagged import BaseTaggableObjectModel
from cosinnus.models.group import CosinnusBaseGroup
from django.core.exceptions import PermissionDenied, ImproperlyConfigured
from django.shortcuts import redirect
from django.http.response import Http404
from cosinnus.utils.exceptions import CosinnusPermissionDeniedException
from cosinnus.core.registries.apps import app_registry
from cosinnus.utils.functions import resolve_class
from django.contrib.auth.models import AnonymousUser


class RequireAdminMixin(object):
    """
    Mixin to ease the use of :meth:`require_admin_access`.

    .. seealso:: :class:`RequireReadMixin`, :class:`RequireWriteMixin`, :class:`RequireCreateObjectsInMixin`
    """

    @require_admin_access()
    def dispatch(self, request, *args, **kwargs):
        return super(RequireAdminMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(RequireAdminMixin, self).get_context_data(**kwargs)
        context.update({'group': self.group})
        return context


class RequireLoggedInMixin(object):
    """
    Mixin to ease the use of :meth:`require_admin_access`.

    .. seealso:: :class:`RequireReadMixin`, :class:`RequireWriteMixin`, :class:`RequireCreateObjectsInMixin`
    """

    @require_logged_in()
    def dispatch(self, request, *args, **kwargs):
        return super(RequireLoggedInMixin, self).dispatch(request, *args, **kwargs)


class RequireVerifiedUserMixin(object):
    """
    Mixin to ease the use of :meth:`require_verified_user_access`.

    .. seealso:: :class:`RequireLoggedInMixin`
    """

    @require_verified_user_access()
    def dispatch(self, request, *args, **kwargs):
        return super(RequireVerifiedUserMixin, self).dispatch(request, *args, **kwargs)


class RequireSuperuserMixin(object):
    """
    Mixin to ease the use of :meth:`require_admin_access`.

    .. seealso:: :class:`RequireReadMixin`, :class:`RequireWriteMixin`, :class:`RequireCreateObjectsInMixin`
    """

    @require_superuser()
    def dispatch(self, request, *args, **kwargs):
        return super(RequireSuperuserMixin, self).dispatch(request, *args, **kwargs)
    

class RequirePortalManagerMixin(object):
    """
    Mixin to ease the use of :meth:`require_portal_manager_access`.

    .. seealso:: :class:`RequireReadMixin`, :class:`RequireWriteMixin`, :class:`RequireCreateObjectsInMixin`
    """

    @require_portal_manager()
    def dispatch(self, request, *args, **kwargs):
        return super(RequirePortalManagerMixin, self).dispatch(request, *args, **kwargs)


class DipatchGroupURLMixin(object):
    """
    Mixin to resolve a group object from its URL without requiring any access priviledges.

    .. seealso:: :class:`RequireAdminMixin`, :class:`RequireWriteMixin`, :class:`RequireCreateObjectsInMixin`
    
    Note: Accessing an object with a slug or pk that is not found will always result in two seperate DB hits,
          because we first do a complete filter for the object, including permissions, pk, group memberships.
          Then, if the object wasn't found, we re-do the filter without permissions to check if that was the 
          cause, then redirect to a login page or a permission denied page. If the second query also fails to
          match anything, we let the Http404 bubble up.
    """

    @dispatch_group_access()
    def dispatch(self, request, *args, **kwargs):
        return super(DipatchGroupURLMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DipatchGroupURLMixin, self).get_context_data(**kwargs)
        context.update({'group': self.group})
        return context


class RequireReadMixin(object):
    """
    Mixin to ease the use of :meth:`require_read_access`.

    .. seealso:: :class:`RequireAdminMixin`, :class:`RequireWriteMixin`, :class:`RequireCreateObjectsInMixin`
    
    Note: Accessing an object with a slug or pk that is not found will always result in two seperate DB hits,
          because we first do a complete filter for the object, including permissions, pk, group memberships.
          Then, if the object wasn't found, we re-do the filter without permissions to check if that was the 
          cause, then redirect to a login page or a permission denied page. If the second query also fails to
          match anything, we let the Http404 bubble up.
    """
    group_url_kwarg = 'group'
    group_attr = 'group'

    @require_read_access()
    def dispatch(self, request, *args, **kwargs):
        try:
            ret = super(RequireReadMixin, self).dispatch(request, *args, **kwargs)
        except CosinnusPermissionDeniedException:
            return redirect_to_not_logged_in(request, view=self)
        return ret 

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
            self.unfiltered_qs = qs
            qs = filter_tagged_object_queryset_for_user(qs, self.request.user)
            
        # very important to set self.queryset to avoid redundant re-filters
        self.queryset = qs
        return qs
    
    def get_object(self, *args, **kwargs):
        # cache object getter because the permission mixins call this method as well as the django view
        if hasattr(self, 'object'):
            return self.object
        
        try:
            obj = super(RequireReadMixin, self).get_object(*args, **kwargs)
        except Http404:
            # we failed to retrieve the object. 
            # if we did permission filtering, try to determine if it was because of a permission error
            unfiltered_qs = getattr(self, 'unfiltered_qs', None)
            if unfiltered_qs:
                kwargs.update({'queryset': unfiltered_qs})
                # if no permission filtering was the cause, this will just bubble as a Http404 (as it should)
                super(RequireReadMixin, self).get_object(*args, **kwargs)
                # otherwise, there is an object, but the user may not access it. redirect to login
                raise CosinnusPermissionDeniedException()
            raise
        
        self.object = obj
        return obj

    
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
    Mixin to ease the use of :meth:`require_write_access`.

    .. seealso:: :class:`RequireAdminMixin`, :class:`RequireReadMixin`, :class:`RequireCreateObjectsInMixin`
    """

    @require_write_access()
    def dispatch(self, request, *args, **kwargs):
        return super(RequireWriteMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(RequireWriteMixin, self).get_context_data(**kwargs)
        context.update({'group': self.group})
        return context
    
    
class RequireWriteGrouplessMixin(object):
    """
    Mixin to ease the use of :meth:`require_write_access_groupless`.
    """

    @require_write_access_groupless()
    def dispatch(self, request, *args, **kwargs):
        return super(RequireWriteGrouplessMixin, self).dispatch(request, *args, **kwargs)


class RequireReadWriteHybridMixin(RequireWriteMixin, RequireReadMixin):
    """
    Combines the functionality of 
        :class:`RequireReadMixin` for GET requests and
        :class:`RequireWriteMixin` for POST requests

    .. seealso:: :class:`RequireAdminMixin`, :class:`RequireReadMixin`, :class:`RequireCreateObjectsInMixin`
    """
    
    def dispatch(self, request, *args, **kwargs):
        if request.method == 'GET':
            return RequireReadMixin.dispatch(self, request, *args, **kwargs)
        else:
            return RequireWriteMixin.dispatch(self, request, *args, **kwargs)

    
    
class RequireCreateObjectsInMixin(object):
    """
    Mixin to ease the use of :meth:`require_create_objects_in_access`.

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


class ModelInheritsGroupReadWritePermissionsMixin(object):
    """
    Mixin for models whose objects should inherit the read/write permissions
    from the group they are in (need a `group` ForeignKey).
    """
    
    def grant_extra_write_permissions(self, user, fields=None):
        return check_object_write_access(self.group, user)
    
    def grant_extra_read_permissions(self, user, fields=None):
        return check_object_read_access(self.group, user)
    

class GroupObjectCountMixin(object):
    """ Adds an ``object_counts`` dict to the context containing the counts of all 
        BaseTaggableObjects in this view's group. 
        Requires ``self.group`` to be set. """
    
    # Object counts as unresolved references to avoid forward dependencies
    # this will check if the cosinnus app is actually present before including it
    app_object_count_mappings = {
        'cosinnus_event': 'cosinnus_event.models.Event',
        'cosinnus_todo': 'cosinnus_todo.models.TodoEntry',
        'cosinnus_file': 'cosinnus_file.models.FileEntry',
        'cosinnus_etherpad': 'cosinnus_etherpad.models.Etherpad',
        'cosinnus_note': 'cosinnus_note.models.Note',
        'cosinnus_poll': 'cosinnus_poll.models.Poll',
        'cosinnus_marketplace': 'cosinnus_marketplace.models.Offer',
        'cosinnus_cloud': True,
    }
    
    def get_context_data(self, **kwargs):
        context = super(GroupObjectCountMixin, self).get_context_data(**kwargs)
        
        object_counts = {}
        for app in app_registry:
            app_name = app_registry.get_name(app) 
            if self.group.is_app_deactivated(app):
                continue
            if app in self.app_object_count_mappings and self.app_object_count_mappings[app] is True:
                object_counts[app_name] = 0
            elif app in self.app_object_count_mappings:
                model = resolve_class(self.app_object_count_mappings[app]) 
                # only for counting the objects, we use a fake superuser, so we get the actual 
                # counts of the contents, and not the visible ones for current user
                fake_admin = AnonymousUser()
                fake_admin.is_superuser = True
                object_counts[app_name] = model.get_current(self.group, fake_admin).count()
        context.update({
            'object_counts': object_counts,
        })
        return context
    

class EndlessPaginationMixin(object):
    """ Support for views using el-pagination (django-el-pagination==2.0)
        Sets self.is_paginated = True if this view is a paginated reload.
        Required class properties:
            ``items_template`` path to template for items that is split from the main view template.
                    See http://django-el-pagination.readthedocs.org/en/latest/twitter_pagination.html#split-the-template """
    
    items_template = None
    is_paginated = False
    
    def dispatch(self, request, *args, **kwargs):
        if not self.items_template:
            raise ImproperlyConfigured('You must supply an ``items_template`` template path for the items that are loaded in pagination.')
        # enable el-pagination items-only rendering
        if request.is_ajax():
            self.template_name = self.items_template
            self.is_paginated = True
        return super(EndlessPaginationMixin, self).dispatch( request, *args, **kwargs)


class GroupIsConferenceMixin(object):
    """ View mixin that makes it required for the view's group to be a conference.
        If not, redirects to the group dashboard. 
        Needs to be in MRO *after* the group-applying `RequireReadMixin` (or similar).  """

    def dispatch(self, request, *args, **kwargs):
        if not self.group.group_is_conference:
            return redirect(group_aware_reverse('cosinnus:group-dashboard', kwargs={'group': self.group}))
        return super().dispatch(request, *args, **kwargs)


class GroupHasBBBActivatedMixin(object):
    """ View mixin that makes it required for the view's group to have a BBB video conferences activated.
        If not, redirects to the group dashboard. """
    
    def dispatch(self, request, *args, **kwargs):
        if not self.group.group_is_conference and not self.group.video_conference_type == CosinnusBaseGroup.BBB_MEETING:
            return redirect(group_aware_reverse('cosinnus:group-dashboard', kwargs={'group': self.group}))
        return super().dispatch(request, *args, **kwargs)
    

class RequireExtraDispatchCheckMixin(object):
    """ View mixin that makes it required for the view's group to be a conference.
        If not, redirects to the group dashboard. 
        Needs to be in MRO *after* the group-applying `RequireReadMixin` (or similar).  """

    def dispatch(self, request, *args, **kwargs):
        return_val = self.extra_dispatch_check()
        if return_val is not None:
            return return_val
        return super().dispatch(request, *args, **kwargs)
    
    def extra_dispatch_check(self):
        """ Stub. Implement this in your view. If anything other than None is returned,
            the dispatch() function will return that value. """
        return None
        
    
