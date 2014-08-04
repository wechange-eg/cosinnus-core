'''
Created on 30.07.2014

@author: Sascha Narr
'''
from django_filters.views import FilterMixin
from django_filters.filterset import FilterSet


class CosinnusFilterMixin(FilterMixin):
    """
    A mixin that provides a way to show and handle a FilterSet in a request.
    """
    filterset_class = None
    
    def get_queryset(self, **kwargs):
        qs = super(CosinnusFilterMixin, self).get_queryset(**kwargs)
        filterset_class = self.get_filterset_class()
        kwargs = {
            'data': self.request.GET or None,
            'queryset': qs
        }
        self.filter = filterset_class(**kwargs)
        qs = self.filter.qs
        return qs
    
    def get_context_data(self, **kwargs):
        context = super(CosinnusFilterMixin, self).get_context_data(**kwargs)
        active_filters = []
        
        """ Add [(filter_param, chosen_value_str)] for displaying current filters """
        for param, value in self.request.GET.items():
            if value and param in self.filter.filters:
                if not 'choices' in self.filter.filters[param].extra:
                    active_filters.append((param, value))
                else:
                    choices_dict = dict([(str(key), val) for key, val in self.filter.filters[param].extra['choices']])
                    chosen_value_str = choices_dict[value]
                    active_filters.append((param, chosen_value_str))
        
        context.update({
            'filter': self.filter,
            'active_filters': active_filters,
        })
        return context

class CosinnusFilterSet(FilterSet):
    
    def get_order_by(self, order_value):
        """ Chain comma-seperated orderings """
        if ',' in order_value:
            return order_value.split(',')
        return super(CosinnusFilterSet, self).get_order_by(order_value)
