# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class UserFormKwargsMixin(object):
    """
    Works nicely together with :class:`cosinnus.forms.GroupKwargModelFormMixin`
    """
    def get_form_kwargs(self):
        kwargs = super(UserFormKwargsMixin, self).get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
