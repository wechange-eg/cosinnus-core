"""
Created on 05.08.2014

@author: Sascha
"""

from builtins import object

from django.utils.translation import gettext_lazy as _
from django_filters.filters import ChoiceFilter

from cosinnus.forms.filters import (
    AllObjectsFilter,
    DropdownChoiceWidget,
    DropdownChoiceWidgetWithEmpty,
    SelectCreatorWidget,
)
from cosinnus.views.mixins.filters import CosinnusFilterSet, CosinnusOrderingFilter
from cosinnus_etherpad.models import Etherpad


class EtherpadFilter(CosinnusFilterSet):
    creator = AllObjectsFilter(label=_('Created By'), widget=SelectCreatorWidget)
    type = ChoiceFilter(
        label=_('Type'), choices=((0, _('Etherpad')), (1, _('Ethercalc'))), widget=DropdownChoiceWidgetWithEmpty
    )

    o = CosinnusOrderingFilter(
        fields=(
            ('last_accessed', 'last_accessed'),
            ('created', 'created'),
            ('title', 'title'),
        ),
        choices=(
            ('-last_accessed', _('Last accessed')),
            ('-created', _('Newest Pads')),
            ('title', _('Title')),
        ),
        default='-last_accessed',
        widget=DropdownChoiceWidget,
    )

    class Meta(object):
        model = Etherpad
        fields = ['creator', 'type', 'o']
