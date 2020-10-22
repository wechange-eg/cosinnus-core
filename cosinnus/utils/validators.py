import re

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext as _


class BSISafePasswordValidator(object):
    """ Password validator to ensure at least the BSI conditions for a chosen password.

    conditions:
    1 symbol character
    1 lowercase character
    1 symbol character

    """

    MIN_SPECIAL_CHARACTERS = 1
    MIN_CAPITAL_LETTERS = 1
    MIN_LOWER_CASE = 1

    def validate(self, password, user=None):
        if not re.findall('\d', password):
            raise ValidationError(
                _("The password must contain at least 1 digit, 0-9."),
                code='password_no_number',
            )
        if not re.findall(r'[A-Z]', password):
            raise ValidationError(
                _("The password must contain at least one upper case character A...Z"),
                code='password_no_uppercase_character'
            )
        if not re.findall(r'[a-z]', password):
            raise ValidationError(
                _("The password must contain at least one lower case character A...Z"),
                code='password_no_lowercase_character'
            )
        if not self.contains_special_character(password):
            raise ValidationError(
                _("The password must contain at least one special character (e.g.: $ § % & ? ! )"),
                code='password_no_special_character'
            )

    def contains_special_character(self, password):
        for char in password.split():
            if char.isalnum():
                return True
        return False

    def get_help_text(self):
        return _(
            "Your password must contain at least: "
            "{upper_case} upper case character, "
            "{lower_case} lower case character, "
            "{special_character} non alpha numerical character.".format(
                upper_case=self.MIN_CAPITAL_LETTERS,
                lower_case=self.MIN_LOWER_CASE,
                special_character=self.MIN_SPECIAL_CHARACTERS
            )
        )
