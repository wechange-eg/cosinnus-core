# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from cosinnus.utils.dashboard import DashboardWidget, DashboardWidgetForm

from cosinnus_marketplace.models import Offer, current_offer_filter


class CurrentOffersForm(DashboardWidgetForm):
    amount = forms.IntegerField(label="Amount", initial=5, min_value=0,
        help_text="0 means unlimited", required=False)
    template_name = 'cosinnus_marketplace/widgets/offer_widget_form.html'
    
    def __init__(self, *args, **kwargs):
        kwargs.pop('group', None)
        super(CurrentOffersForm, self).__init__(*args, **kwargs)


class CurrentOffers(DashboardWidget):

    app_name = 'marketplace'
    form_class = CurrentOffersForm
    model = Offer
    title = _('Current Offers')
    user_model_attr = None  # No filtering on user page
    widget_name = 'current'
    template_name = 'cosinnus_marketplace/widgets/current.html'
    
    def get_data(self, offset=0):
        """ Returns a tuple (data, rows_returned, has_more) of the rendered data and how many items were returned.
            if has_more == False, the receiving widget will assume no further data can be loaded.
         """
        count = int(self.config['amount'])
        all_current_offers = self.get_queryset().\
                order_by('-created').\
                select_related('group').all()
        offers = all_current_offers
        
        if count != 0:
            offers = offers.all()[offset:offset+count]
        
        data = {
            'offers': offers,
            'all_current_offers': all_current_offers,
            'no_data': _('No current offers'),
            'group': self.config.group,
        }
        return (render_to_string(self.template_name, data), len(offers), len(offers) >= count)

    def get_queryset(self):
        qs = super(CurrentOffers, self).get_queryset()
        return current_offer_filter(qs)
