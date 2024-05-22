# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object

from cosinnus.forms.attached_object import FormAttachableMixin
from cosinnus.forms.group import GroupKwargModelFormMixin
from cosinnus.forms.tagged import BaseTaggableObjectForm, get_form
from cosinnus.forms.user import UserKwargModelFormMixin
from cosinnus_etherpad.models import Etherpad


class _EtherpadForm(GroupKwargModelFormMixin, UserKwargModelFormMixin, FormAttachableMixin, BaseTaggableObjectForm):
    class Meta(object):
        model = Etherpad
        fields = ('title', 'description', 'media_tag')

    # TODO: Uncomment this to re-enable protecting the title of a pad
    # def __init__(self, *args, **kwargs):
    # super(_EtherpadForm, self).__init__(*args, **kwargs)
    # if self.instance.pk:
    #    self.fields['title'].widget.attrs['readonly'] = True

    # TODO: Uncomment this to re-enable protecting the title of a pad
    # def clean_title(self):
    #    if self.instance.pk:
    #        return self.instance.title
    #    else:
    #        return self.cleaned_data['title']


EtherpadForm = get_form(_EtherpadForm)
