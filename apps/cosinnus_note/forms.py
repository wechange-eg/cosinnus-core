# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from django import forms

from cosinnus.forms.attached_object import FormAttachableMixin
from cosinnus.forms.group import GroupKwargModelFormMixin
from cosinnus.forms.tagged import get_form, BaseTaggableObjectForm
from cosinnus.forms.user import UserKwargModelFormMixin

from cosinnus_note.models import Comment, Note

from cosinnus.forms.translations import TranslatedFieldsFormMixin


class _NoteForm(TranslatedFieldsFormMixin, GroupKwargModelFormMixin, UserKwargModelFormMixin,
                FormAttachableMixin, BaseTaggableObjectForm):
    
    # HTML required attribute disabled because of the model-required but form-optional field 'title'
    use_required_attribute = False 
    
    class Meta(object):
        model = Note
        fields = ('title', 'text', 'video',)
        
    
    def __init__(self, *args, **kwargs):
        super(_NoteForm, self).__init__(*args, **kwargs)
        if 'title' in self.initial and self.initial['title'] == Note.EMPTY_TITLE_PLACEHOLDER:
            self.initial['title'] = ''
        if self.fields['title'].initial == Note.EMPTY_TITLE_PLACEHOLDER:
            self.fields['title'].initial = ''

    def clean(self):
        """ Insert a placeholder title if no title is given """
        title = self.cleaned_data.get('title', None)
        if not title:
            note_text = self.cleaned_data.get('text', None)
            if note_text:
                self.cleaned_data.update({'title': Note.EMPTY_TITLE_PLACEHOLDER},)
                self.errors.pop('title', None)
        return super(_NoteForm, self).clean()


#: A django-multiform :class:`MultiModelForm`. Includs support for `group` and
#: `attached_objects_querysets` arguments being passed to the underlying main
#: form (:class:`_NoteForm`)
NoteForm = get_form(_NoteForm)


class CommentForm(forms.ModelForm):

    class Meta(object):
        model = Comment
        fields = ('text',)
