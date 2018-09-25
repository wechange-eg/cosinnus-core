# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms
from django.forms.widgets import SplitDateTimeWidget 
from cosinnus.forms.widgets import SplitHiddenDateWidget



class SimpleDateWidget(SplitDateTimeWidget):
    """
    A Widget that splits datetime input into two <input type="text"> boxes.
    """

class SimpleStatisticsForm(forms.Form):
    
    from_date = forms.SplitDateTimeField(widget=SplitHiddenDateWidget)
    to_date = forms.SplitDateTimeField(widget=SplitHiddenDateWidget)
    
    
