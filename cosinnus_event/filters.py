'''
Created on 05.08.2014

@author: Sascha
'''
from builtins import object
from django.utils.translation import ugettext_lazy as _

from cosinnus.views.mixins.filters import CosinnusFilterSet,\
    CosinnusOrderingFilter
from cosinnus.forms.filters import AllObjectsFilter, SelectCreatorWidget,\
    DropdownChoiceWidget
from cosinnus_event.models import Event


class EventFilter(CosinnusFilterSet):
    creator = AllObjectsFilter(label=_('Created By'), widget=SelectCreatorWidget)
    
    o = CosinnusOrderingFilter(
        fields=(
            ('from_date', 'from_date'),
            ('created', 'created'),
            ('title', 'title'),
        ),
        choices=(
            ('-from_date', _('Soonest Upcoming')),
            ('-created', _('Newest Created')),
            ('title', _('Title')),
        ),
        default='-from_date',
        widget=DropdownChoiceWidget
    )
    
    class Meta(object):
        model = Event
        fields = ['creator', 'o']
    
