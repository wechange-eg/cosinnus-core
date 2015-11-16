'''
Created on 30.07.2014

@author: Sascha Narr
'''
from django_filters.views import FilterMixin
from django_filters.filterset import FilterSet
from cosinnus.forms.filters import DropdownChoiceWidget

from django import forms
from django.utils.text import capfirst
from django.utils.translation import ugettext as _
from cosinnus.models.tagged import BaseHierarchicalTaggableObjectModel

class CosinnusFilterMixin(FilterMixin):
    """
    A mixin that provides a way to show and handle a FilterSet in a request.
    """
    filterset_class = None
    
    def get_queryset(self, **kwargs):
        base_qs = super(CosinnusFilterMixin, self).get_queryset(**kwargs)
        filterset_class = self.get_filterset_class()
        kwargs = {
            'data': self.request.GET or None,
            'queryset': base_qs,
            'group': getattr(self, 'group', None)
        }
        self.filter = filterset_class(**kwargs)
        qs = self.filter.qs
        
        # support for Containers in BaseHierarchical models (keep Containers in QS!)
        if BaseHierarchicalTaggableObjectModel in self.model.__bases__:
            qs = base_qs.filter(is_container=True) | qs
        
        return qs
    
    def get_context_data(self, **kwargs):
        context = super(CosinnusFilterMixin, self).get_context_data(**kwargs)
        active_filters = []
        
        """ Add [(filter_param, chosen_value_str, label, type<'sort'|'filter'>)] for displaying current filters """
        for param, value in self.filter.data.items():
            if value and param in self.filter.filters:
                if not 'choices' in self.filter.filters[param].extra:
                    active_filters.append((param, value, self.filter.filters[param].label, 'filter'))
                else:
                    choices_dict = dict([(str(key), val) for key, val in self.filter.filters[param].extra['choices']])
                    if value in choices_dict:
                        format_func = getattr(self.filter.filters[param].field.widget, 'format_label_value', None)
                        if callable(format_func):
                            chosen_value_str = format_func(choices_dict[value])
                        else:
                            chosen_value_str = choices_dict[value]
                        active_filters.append((param, chosen_value_str, self.filter.filters[param].label, 'filter'))
            if value and param == self.filter.order_by_field:
                ordering_choices_dict = dict(self.filter.ordering_field.choices)
                if value in ordering_choices_dict:
                    chosen_value_str = ordering_choices_dict[value]
                    active_filters.append((param, chosen_value_str, self.filter.ordering_field.label, 'sort'))
                
        
        context.update({
            'filter': self.filter,
            'active_filters': active_filters,
        })
        return context

class CosinnusFilterSet(FilterSet):
    
    def __init__(self, data=None, queryset=None, prefix=None, strict=None, group=None):
        """ Add a reference to the form to the form's widgets """
        self.group = group
        super(CosinnusFilterSet, self).__init__(data, queryset, prefix, strict)
        for name, filter_obj in self.filters.items():
            filter_obj.group = group
        for field in self.form.fields.values():
            field.widget.form_instance = self.form
    
    def get_order_by(self, order_value):
        """ Chain comma-seperated orderings """
        if ',' in order_value:
            return order_value.split(',')
        return super(CosinnusFilterSet, self).get_order_by(order_value)
    
    def get_ordering_field(self):
        """ Overriding BaseFilterSet """
        if self._meta.order_by:
            if isinstance(self._meta.order_by, (list, tuple)):
                if isinstance(self._meta.order_by[0], (list, tuple)):
                    # e.g. (('field', 'Display name'), ...)
                    choices = [(f[0], f[1]) for f in self._meta.order_by]
                else:
                    choices = [(f, _('%s (descending)' % capfirst(f[1:])) if f[0] == '-' else capfirst(f))
                               for f in self._meta.order_by]
            else:
                # add asc and desc field names
                # use the filter's label if provided
                choices = []
                for f, fltr in self.filters.items():
                    choices.extend([
                        (fltr.name or f, fltr.label or capfirst(f)),
                        ("-%s" % (fltr.name or f), _('%s (descending)' % (fltr.label or capfirst(f))))
                    ])
            return forms.ChoiceField(label=_("Ordering"), required=False,
                                     choices=choices, widget=DropdownChoiceWidget)
    
