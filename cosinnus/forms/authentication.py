# -*- coding: utf-8 -*-

from two_factor.forms import DisableForm

from cosinnus.forms.mixins import PasswordValidationFormMixin


class DisableFormWithPasswordValidation(PasswordValidationFormMixin, DisableForm):
    """ The 2-fa disable form, with added password validation logic """
    pass
