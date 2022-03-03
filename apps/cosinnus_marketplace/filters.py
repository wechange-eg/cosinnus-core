'''
Created on 05.08.2014

@author: Sascha
'''
from builtins import object
from django.utils.translation import ugettext_lazy as _

from cosinnus.views.mixins.filters import CosinnusFilterSet,\
    CosinnusOrderingFilter
from cosinnus.forms.filters import AllObjectsFilter, SelectCreatorWidget,\
    DropdownChoiceWidgetWithEmpty, DropdownChoiceWidget
from cosinnus_marketplace.models import Offer, get_categories_grouped
from django_filters.filters import ChoiceFilter


class OfferFilter(CosinnusFilterSet):
    creator = AllObjectsFilter(label=_('Created By'), widget=SelectCreatorWidget)
    type = ChoiceFilter(label=_('Type'), choices=Offer.TYPE_CHOICES, widget=DropdownChoiceWidgetWithEmpty)
    
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
        model = Offer
        fields = ['creator', 'type', 'categories', 'o']
    
    def get_categories_grouped(self):
        return get_categories_grouped(self.form.fields['categories']._queryset)
    