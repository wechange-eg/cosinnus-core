# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from cosinnus_file.models import FileEntry
import logging

from django import forms
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import URLValidator
from django.utils.translation import ugettext_lazy as _

from cosinnus.forms.group import GroupKwargModelFormMixin
from cosinnus.forms.tagged import get_form, BaseTaggableObjectForm
from cosinnus.forms.user import UserKwargModelFormMixin
from cosinnus.utils.validators import validate_file_infection


logger = logging.getLogger('cosinnus')


class _FileForm(GroupKwargModelFormMixin, UserKwargModelFormMixin,
                BaseTaggableObjectForm):
    
    optional_fields = ['title', 'file', 'note', 'url']
    
    file = forms.FileField(validators=[validate_file_infection])
    url = forms.URLField(widget=forms.TextInput, required=False)

    class Meta(object):
        model = FileEntry
        fields = ('title', 'file', 'note', 'url')

    def __init__(self, *args, **kwargs):
        super(_FileForm, self).__init__(*args, **kwargs)
        # make optional fields not required
        for field_name in self.optional_fields:
            self.fields[field_name].required = False
        # hide the file upload field on folders, and set the folder flag
        if self.instance.is_container or \
                'initial' in kwargs and 'is_container' in kwargs['initial'] and \
                kwargs['initial']['is_container']:
            del self.fields['file']
            del self.fields['url']
            self.instance.is_container = True

    def clean_is_container(self):
        if self.instance:
            return self.cleaned_data['is_container']

    def clean_file(self):
        fileupload = self.cleaned_data['file']
        if fileupload and isinstance(fileupload, UploadedFile):
            max_length = self._meta.model._meta.get_field('_sourcefilename').max_length
            name = fileupload._name
            # shorten file name before its file suffix if it is too long
            if len(name) > max_length:
                if '.' in fileupload._name:
                    filename, suffix = name.rsplit('.', 1)
                    test = '.'.join([filename[:max_length-len(suffix)-1], suffix])
                    fileupload._name = test
                else:
                    fileupload._name = name[:max_length]
            if self.instance:
                self.instance.mimetype = fileupload.content_type
        return fileupload
    
    def clean_url(self):
        url = self.data.get('url', None)
        if url:
            url = url.strip()
            if not url.startswith('http'):
                url = 'https://%s' % url
            msg = _('The given URL does not seem to be valid.')
            validate = URLValidator(message=msg)
            validate(url)
        return url
    
    def clean(self):
        """ Insert the filename as title if no title is given """
        fileupload = self.cleaned_data.get('file', None)
        url = self.cleaned_data.get('url', None)
        title = self.cleaned_data.get('title', None)
        is_container = self.cleaned_data.get('is_container', None)
        # url or file is required
        if not url and not fileupload and not is_container:
            raise ValidationError(_('Must supply either a URL or File'))
        if not title:
            if fileupload:
                self.cleaned_data.update({'title': fileupload._name},)
                self.errors.pop('title', None)
            if url:
                self.cleaned_data.update({'title': url},)
                self.errors.pop('title', None)
        return super(_FileForm, self).clean()
    
FileForm = get_form(_FileForm, attachable=False)


class FileListForm(forms.Form):

    # required=False to handle the validation in the view
    select = forms.MultipleChoiceField(required=False)
