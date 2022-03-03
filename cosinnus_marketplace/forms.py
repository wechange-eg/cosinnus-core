# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from django import forms
from django.utils.translation import ugettext_lazy as _

from cosinnus.forms.group import GroupKwargModelFormMixin
from cosinnus.forms.tagged import get_form, BaseTaggableObjectForm
from cosinnus.forms.user import UserKwargModelFormMixin

from cosinnus_marketplace.models import Offer, Comment, get_categories_grouped,\
    OfferCategory
from cosinnus.forms.attached_object import FormAttachableMixin


class _OfferForm(GroupKwargModelFormMixin, UserKwargModelFormMixin,
                 FormAttachableMixin, BaseTaggableObjectForm):
    
    class Meta(object):
        model = Offer
        fields = ('type', 'title', 'description', 'phone_number', 'is_active', 'categories')
    
    def clean(self, *args, **kwargs):
        cleaned_data = super(_OfferForm, self).clean(*args, **kwargs)
        return cleaned_data
    
    def get_categories_grouped(self):
        return get_categories_grouped(OfferCategory.objects.all())
        
OfferForm = get_form(_OfferForm)


class OfferNoFieldForm(forms.ModelForm):

    class Meta(object):
        model = Offer
        fields = ()

        
class CommentForm(forms.ModelForm):

    class Meta(object):
        model = Comment
        fields = ('text',)

