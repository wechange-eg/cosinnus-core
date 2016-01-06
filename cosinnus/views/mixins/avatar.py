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
            setattr(form.instance, self.avatar_field_name, None)
        elif self.avatar_field_name+'-ratio' in form.data and form.data[self.avatar_field_name+'-ratio']:
            avatar_field = AvatarField()
            avatar_field.name = self.avatar_field_name
            try:
                avatar_field.save_form_data(form.instance, form.cleaned_data['obj'][self.avatar_field_name])
            except SystemError:
                messages.error(self.request, _('There was an error while processing your avatar. Please make sure you selected a large enough part of the image!'))
            except IOError:
                messages.error(self.request, _('There was an error while processing your avatar. The image file might be broken or the file transfer was interrupted.'))
    
    def _reset_awesome_avatar(self, form):
        if self.object:
            initial_obj = self.object.__class__.objects.get(id=self.object.id)
            setattr(self.object, self.avatar_field_name, getattr(initial_obj, self.avatar_field_name)) 
    
    def form_valid(self, form):
        self._save_awesome_avatar(form)
        return super(AvatarFormMixin, self).form_valid(form)
        
    def forms_valid(self, form, inlines):
        self._save_awesome_avatar(form)
        return super(AvatarFormMixin, self).forms_valid(form, inlines)

    def form_invalid(self, form):
        # reset avatar. can't find another way to carry it over right now.
        self._reset_awesome_avatar(form)
        return super(AvatarFormMixin, self).form_invalid(form)
        
    def forms_invalid(self, form, inlines):
        # reset avatar. can't find another way to carry it over right now.
        self._reset_awesome_avatar(form)
        return super(AvatarFormMixin, self).forms_invalid(form, inlines)
