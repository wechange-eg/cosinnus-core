# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object

from django import forms

from cosinnus.forms.group import AsssignPortalMixin
from cosinnus.forms.tagged import get_form
from cosinnus.models.idea import CosinnusIdea


class _CosinnusIdeaForm(AsssignPortalMixin, forms.ModelForm):
    class Meta(object):
        model = CosinnusIdea
        fields = [
            'title',
            'description',
            'image',
            'public',
        ]


CosinnusIdeaForm = get_form(_CosinnusIdeaForm, attachable=False)
