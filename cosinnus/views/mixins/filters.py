"""
Created on 30.07.2014

@author: Sascha Narr
"""

from builtins import str

from django import forms
from django.http.request import QueryDict
from django_filters.filters import OrderingFilter
from django_filters.filterset import FilterSet
from django_filters.views import FilterMixin

from cosinnus.models.tagged import BaseHierarchicalTaggableObjectModel
from cosinnus.utils.permissions import filter_base_taggable_qs_for_blocked_user_content


class CosinnusFilterMixin(FilterMixin):
    """
    A mixin that provides a way to show and handle a FilterSet in a request.
    """

    filterset_class = None

    def get_queryset(self, **kwargs):
        base_qs = super(CosinnusFilterMixin, self).get_queryset(**kwargs)
        filterset_class = self.get_filterset_class()
        kwargs = {'data': self.request.GET or None, 'queryset': base_qs, 'group': getattr(self, 'group', None)}
        self.filter = filterset_class(**kwargs)
        qs = self.filter.qs

        # support for Containers in BaseHierarchical models (keep Containers in QS!)
        if BaseHierarchicalTaggableObjectModel in self.model.__bases__:
            qs = base_qs.filter(is_container=True) | qs

        # support for filtering out blocked users' content
        qs = filter_base_taggable_qs_for_blocked_user_content(qs, self.request.user)

        return qs

    def get_context_data(self, **kwargs):
        context = super(CosinnusFilterMixin, self).get_context_data(**kwargs)
        active_filters = []

        """ Add [(filter_param, chosen_value_str, label, type<'sort'|'filter'>)] for displaying current filters """
        for param, value in list(self.filter.data.items()):
            if value and param in self.filter.filters:
                active_filter = self.filter.filters[param]
                if 'choices' not in active_filter.extra:
                    active_filters.append((param, value, active_filter.label, 'filter'))
                else:
                    choices_dict = dict([(str(key), val) for key, val in active_filter.extra['choices']])
                    if value in choices_dict:
                        format_func = getattr(active_filter.field.widget, 'format_label_value', None)
                        if callable(format_func):
                            chosen_value_str = format_func(choices_dict[value])
                        else:
                            chosen_value_str = choices_dict[value]
                        active_filters.append((param, chosen_value_str, active_filter.label, 'filter'))
                active_filter_type = type(active_filter)
                if (active_filter_type is OrderingFilter) or (OrderingFilter in active_filter_type.__bases__):
                    ordering_choices_dict = active_filter.extra['choices']
                    if value in ordering_choices_dict:
                        chosen_value_str = ordering_choices_dict[value]
                        active_filters.append((param, chosen_value_str, active_filter.label, 'sort'))

        context.update(
            {
                'filter': self.filter,
                'active_filters': active_filters,
            }
        )
        return context


class CosinnusFilterSet(FilterSet):
    hidden_filters = []

    def __init__(self, data=None, queryset=None, prefix=None, group=None):
        """Add a reference to the form to the form's widgets"""
        self.group = group
        # this forces the filtering to apply even with no GET args, and enables filtering defaults
        if not data:
            data = QueryDict('', mutable=True)
            data.update({field: '' for field in self._meta.fields})
        super(CosinnusFilterSet, self).__init__(data=data, queryset=queryset, prefix=prefix)
        for name, filter_obj in list(self.filters.items()):
            filter_obj.group = group
        for field in list(self.form.fields.values()):
            field.widget.form_instance = self.form
        # hide selected filters
        if self.hidden_filters:
            for filter_name in self.hidden_filters:
                self.form.fields[filter_name].widget = forms.HiddenInput()


class CosinnusOrderingFilter(OrderingFilter):
    """An ordering filter that supports a default ordering value if no orderin is chosen"""

    default = None

    def __init__(self, *args, **kwargs):
        self.default = kwargs.pop('default', None)
        super(CosinnusOrderingFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        if not value and self.default:
            return qs.order_by(self.default)
        return super(CosinnusOrderingFilter, self).filter(qs, value)
