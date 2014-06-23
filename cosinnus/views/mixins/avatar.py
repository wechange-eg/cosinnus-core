# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from awesome_avatar.fields import AvatarField

class AvatarFormMixin(object):
    """
    Mix this into your create/update views that contain forms with AvatarFields.
    """
    
    avatar_field_name = 'avatar'
    
    def form_valid(self, form):
        if form.data.get(self.avatar_field_name+'_clear'):
            setattr(form.instance, 'avatar', None)
        elif self.avatar_field_name+'-ratio' in form.data and form.data[self.avatar_field_name+'-ratio']:
            avatar_field = AvatarField()
            avatar_field.name = self.avatar_field_name
            avatar_field.save_form_data(form.instance, form.cleaned_data['obj'][self.avatar_field_name])
        ret = super(AvatarFormMixin, self).form_valid(form)
        return ret
