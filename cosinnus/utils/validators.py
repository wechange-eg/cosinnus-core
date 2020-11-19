import re

from django import forms
from django.utils.translation import ugettext as _


class BSISafePasswordValidator(object):
    """ Password validator to ensure at least the BSI conditions for a chosen password.

    conditions:
    1 symbol character
    1 lowercase character
    1 uppercase character
    1 digit
    """

    MIN_SPECIAL_CHARACTERS = 1
    MIN_CAPITAL_LETTERS = 1
    MIN_LOWER_CASE = 1

    def validate(self, password, user=None):
        if not re.findall('\d', password):
            raise forms.ValidationError(
                _("The password must contain at least 1 digit, 0-9."),
                code='password_no_number',
            )
        if not re.findall(r'[A-Z]', password):
            raise forms.ValidationError(
                _("The password must contain at least one upper case character A...Z"),
                code='password_no_uppercase_character'
            )
        if not re.findall(r'[a-z]', password):
            raise forms.ValidationError(
                _("The password must contain at least one lower case character A...Z"),
                code='password_no_lowercase_character'
            )
        if not self.contains_special_character(password):
            raise forms.ValidationError(
                _("The password must contain at least one special character (e.g.: $ § % & ? ! )"),
                code='password_no_special_character'
            )

    @staticmethod
    def contains_special_character(password):
        for char in password.split():
            if not char.isalnum():
                return True
        return False
