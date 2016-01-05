# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from awesome_avatar.fields import AvatarField
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _

class AvatarFormMixin(object):
    """
    Mix this into your create/update views that contain forms with AvatarFields.
    """
    
    avatar_field_name = 'avatar'
    
    def _save_awesome_avatar(self, form):
        if form.data.get(self.avatar_field_name+'_clear', 'false') != "false":
            setattr(form.instance, 'avatar', None)
        elif self.avatar_field_name+'-ratio' in form.data and form.data[self.avatar_field_name+'-ratio']:
            avatar_field = AvatarField()
            avatar_field.name = self.avatar_field_name
            try:
                avatar_field.save_form_data(form.instance, form.cleaned_data['obj'][self.avatar_field_name])
            except SystemError:
                messages.error(self.request, _('There was an error while processing your avatar. Please make sure you selected a large enough part of the image!'))
            except IOError:
                messages.error(self.request, _('There was an error while processing your avatar. The image file might be broken or the file transfer was interrupted.'))
    
    def form_valid(self, form):
        self._save_awesome_avatar(form)
        return super(AvatarFormMixin, self).form_valid(form)
    
    def forms_valid(self, form, inlines):
        self._save_awesome_avatar(form)
        return super(AvatarFormMixin, self).forms_valid(form, inlines)
