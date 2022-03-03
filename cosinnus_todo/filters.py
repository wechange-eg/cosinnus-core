'''
Created on 05.08.2014

@author: Sascha
'''
from builtins import object
from django.utils.translation import ugettext_lazy as _

from cosinnus.views.mixins.filters import CosinnusFilterSet,\
    CosinnusOrderingFilter
from cosinnus.forms.filters import AllObjectsFilter, SelectCreatorWidget,\
    SelectUserWidget, DropdownChoiceWidget, ForwardDateRangeFilter,\
    DropdownChoiceWidgetWithEmpty
from cosinnus_todo.models import TodoEntry, PRIORITY_CHOICES
from django_filters.filters import ChoiceFilter

FILTER_PRIORITY_CHOICES = list(PRIORITY_CHOICES)

FILTER_COMPLETED_CHOICES = list((
    ('0', _('Open')),
    ('1', _('Completed')),
    ('all', _('All')),
))

class IsCompletedFilter(ChoiceFilter):
    
    def filter(self, qs, value):
        filter_value = '' if value == 'all' else value
        return super(IsCompletedFilter, self).filter(qs, filter_value)


class TodoOrderingFilter(CosinnusOrderingFilter):

    def filter(self, qs, value):
        if value == '-priority':
            return qs.order_by('-priority', 'due_date')
        return super(TodoOrderingFilter, self).filter(qs, value)
    
    
class TodoFilter(CosinnusFilterSet):
    creator = AllObjectsFilter(label=_('Created By'), widget=SelectCreatorWidget)
    assigned_to = AllObjectsFilter(label=_('Assigned To'), widget=SelectUserWidget)
    priority = ChoiceFilter(label=_('Priority'), choices=FILTER_PRIORITY_CHOICES, widget=DropdownChoiceWidget)
    due_date = ForwardDateRangeFilter(label=_('Due date'), widget=DropdownChoiceWidget)
    is_completed = IsCompletedFilter(label=_('Status'), choices=FILTER_COMPLETED_CHOICES, widget=DropdownChoiceWidgetWithEmpty())
    
    o = TodoOrderingFilter(
        fields=(
            ('created', 'created'),
            ('priority', 'priority'),
            ('due_date', 'due_date'),
            ('title', 'title'),
        ),
        choices=(
            ('-created', _('Newest Created')),
            ('title', _('Title')),
            ('-priority', _('Priority')),
            ('due_date', _('Soonest Due'))
        ),
        default='-created',
        widget=DropdownChoiceWidget
    )
    
    class Meta(object):
        model = TodoEntry
        fields = ['creator', 'assigned_to', 'priority', 'due_date', 'is_completed', 'o']

    
    