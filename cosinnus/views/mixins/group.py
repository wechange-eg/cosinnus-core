# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.core.decorators.views import require_populate_group


class RequireGroupMixin(object):
    """This mixin combines the :py:func:`staff_required` and
    :py:func:`require_populate_group` decorators and also puts the group
    (resolved) by :py:func:`require_populate_group` to the render context. Each
    CBV that requires a group given as part of the URL should use this mixin.
    """

    @require_populate_group()
    def dispatch(self, request, *args, **kwargs):
        return super(RequireGroupMixin, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(RequireGroupMixin, self).get_context_data(**kwargs)
        context.update({'group': self.group})
        return context


class FilterGroupMixin(object):
    """Filters the underlying queryset so that only models referring to the
    given group are returned.
    """

    #: See `group_attr` of :py:func:`require_populate_group` for usage
    group_attr = 'group'
    #: The actual filter keyword used in the queryset's `filter` function
    group_field = 'group'

    def get_queryset(self, **kwargs):
        return super(FilterGroupMixin, self).get_queryset().filter(
            **{self.get_group_field(): self.get_group_attr()})

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
        kwargs.update({"group": self.group})
        return kwargs
