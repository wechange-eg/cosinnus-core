# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from builtins import object
from cosinnus.forms.tagged import BaseTaggableObjectForm
from cosinnus.forms.user import UserKwargModelFormMixin
from cosinnus.forms.tagged import get_form
from cosinnus_stream.models import Stream


class _StreamForm(UserKwargModelFormMixin, BaseTaggableObjectForm):

    class Meta(object):
        model = Stream
        fields = ('title', 'group', 'models',)
        
    def clean_models(self):
        models = self.data.getlist('models')
        return ','.join(models)

StreamForm = get_form(_StreamForm)
