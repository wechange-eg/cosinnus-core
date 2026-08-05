import logging
import re

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.encoding import force_str
from django.utils.translation import gettext as _
from django_clamd.validators import validate_file_infection as clamd_validate_file_infection
from PIL import Image, UnidentifiedImageError
from PIL.Image import DecompressionBombError

from cosinnus.conf import settings

logger = logging.getLogger('cosinnus')


class BSISafePasswordValidator(object):
    """Password validator to ensure at least the BSI conditions for a chosen password.

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
                _('The password must contain at least 1 digit, 0-9.'),
                code='password_no_number',
            )
        if not re.findall(r'[A-Z]', password):
            raise forms.ValidationError(
                _('The password must contain at least one upper case character A...Z'),
                code='password_no_uppercase_character',
            )
        if not re.findall(r'[a-z]', password):
            raise forms.ValidationError(
                _('The password must contain at least one lower case character A...Z'),
                code='password_no_lowercase_character',
            )
        if not self.contains_special_character(password):
            raise forms.ValidationError(
                _('The password must contain at least one special character (e.g.: $ § % & ? ! )'),
                code='password_no_special_character',
            )

    @staticmethod
    def contains_special_character(password):
        for char in password.split():
            if not char.isalnum():
                return True
        return False

    def get_help_text(self):
        return _(
            'Your password must contain at least: '
            '{upper_case} upper case character, '
            '{lower_case} lower case character, '
            '{special_character} non alpha numerical character.'.format(
                upper_case=self.MIN_CAPITAL_LETTERS,
                lower_case=self.MIN_LOWER_CASE,
                special_character=self.MIN_SPECIAL_CHARACTERS,
            )
        )


def validate_file_infection(file):
    if getattr(settings, 'COSINNUS_VIRUS_SCAN_UPLOADED_FILES', False):
        try:
            return clamd_validate_file_infection(file)
        except ValidationError:
            raise
        except Exception as e:
            logger.error(
                'Error during file upload: django-clamd infection validation failed for uploaded file!',
                extra={'uploaded-file': str(file), 'exception': e},
            )


def validate_image_format(file):
    """
    :param file: File object or dict with item `'file': file-object`
    """
    # Image.open will raise an exception if dimensions exceed two times this limit
    generic_error_message = _(
        'Error during image processing. Your image may be too large, in an unsupported format, or corrupt.'
    )
    Image.MAX_IMAGE_PIXELS = 15_000_000  # abort if more than 2*15 MegaPixel
    max_file_size = 20_971_520  # 20 MBytes

    # awesome_avatar returns a dict with box coordinates and file
    if isinstance(file, dict):
        file = file.get('file', None)

    if not file:
        return

    try:
        file.seek(0)

        # abort if file is larger than 20MBytes
        if file.size > max_file_size:
            raise ValueError('File too large')

        # do preliminary checks on image format
        pil_img = Image.open(file)
        pil_img.verify()

        # open the image again, since verify does make the object unusable
        file.seek(0)
        pil_img = Image.open(file)

        # return "common" image modes
        # see https://pillow.readthedocs.io/en/stable/handbook/concepts.html#concept-modes
        if pil_img.mode not in ['1', 'L', 'P', 'RGB', 'RGBA']:
            raise ValueError('Unsupported Mode')
    except (ValidationError, ValueError, DecompressionBombError, UnidentifiedImageError):
        raise ValidationError(generic_error_message)
    except Exception as e:
        logger.error('Unexpected Error during image processing', extra={'exception': force_str(e)})
        raise ValidationError(generic_error_message)
    finally:
        file.seek(0)


class CleanFromToDateFieldsMixin(object):
    """Mixin for a ModelForm with a from_date and to_date field that checks the validity
    of the date range"""

    from_date_field_name = 'from_date'
    to_date_field_name = 'to_date'

    def clean(self):
        cleaned_data = super().clean()
        from_date = cleaned_data.get(self.from_date_field_name)
        to_date = cleaned_data.get(self.to_date_field_name)

        if to_date and from_date:
            if to_date <= from_date:
                msg = _('The start date must be before the end date')
                self.add_error(self.to_date_field_name, msg)

        elif to_date and not from_date:
            msg = _('Please also provide a start date')
            self.add_error(self.from_date_field_name, msg)

        elif from_date and not to_date:
            msg = _('Please also provide an end date')
            self.add_error(self.to_date_field_name, msg)

        return cleaned_data


def validate_username(value):
    """A simple validator to reduce possible spam attempts in usernames."""
    disallowed_strings = ['/', 'http', 'www', '<', '>']
    if any([fragment in value for fragment in disallowed_strings]) or value.count('.') > 1:
        raise ValidationError(
            _('Ensure that your name does not contain any invalid characters.'),
            code='invalid_username',
        )


class HexColorValidator(RegexValidator):
    """Validator that checks for a proper hex code, with optional "#" prefix."""

    def __init__(self):
        super().__init__('^#?(?:[0-9a-fA-F]{3}){1,2}$')
