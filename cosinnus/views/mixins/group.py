# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.core.decorators.views import (require_read_access,
    require_write_access, require_admin_access)


class RequireAdminMixin(object):
    """
    Mixing to ease the use of :meth:`require_admin_access`.

    .. seealso:: :class:`RequireReadMixin`, :class:`RequireWriteMixin`
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

    .. seealso:: :class:`RequireAdminMixin`, :class:`RequireWriteMixin`
    """

    @require_read_access()
    def dispatch(self, request, *args, **kwargs):
        return super(RequireReadMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(RequireReadMixin, self).get_context_data(**kwargs)
        context.update({'group': self.group})
        return context


class RequireWriteMixin(object):
    """
    Mixing to ease the use of :meth:`require_write_access`.

    .. seealso:: :class:`RequireAdminMixin`, :class:`RequireReadMixin`
    """

    @require_write_access()
    def dispatch(self, request, *args, **kwargs):
        return super(RequireWriteMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(RequireWriteMixin, self).get_context_data(**kwargs)
        context.update({'group': self.group})
        return context


class FilterGroupMixin(object):
    """Filters the underlying queryset so that only models referring to the
    given group are returned.
    """

    #: See `group_attr` of :py:func:`require_read_access` and similar for usage
    group_attr = 'group'
    #: The actual filter keyword used in the queryset's `filter` function
    group_field = 'group'

    def get_queryset(self, **kwargs):
        fkwargs = {self.get_group_field(): self.get_group_attr()}

        select_related = set(kwargs.pop('select_related', ()))
        select_related.add(self.get_group_field())

        return super(FilterGroupMixin, self).get_queryset() \
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
