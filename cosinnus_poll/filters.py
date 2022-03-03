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
from cosinnus_poll.models import Poll


class PollFilter(CosinnusFilterSet):
    creator = AllObjectsFilter(label=_('Created By'), widget=SelectCreatorWidget)
    
    o = CosinnusOrderingFilter(
        fields=(
            ('created', 'created'),
            ('title', 'title'),
        ),
        choices=(
            ('-created', _('Newest Created')),
            ('title', _('Title')),
        ),
        default='-created',
        widget=DropdownChoiceWidget
    )
    
    class Meta(object):
        model = Poll
        fields = ['creator', 'o']
    
