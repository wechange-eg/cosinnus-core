# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.formats import get_format

from rest_framework.fields import DateField, DateTimeField, TimeField

from cosinnus.utils.dates import datetime_format_js2py


__all__ = ('BaseL10NField', 'DateL10nField', 'DateTimeL10nField',
    'TimeL10nField')


class BaseL10NField(object):
    format_key = None

    def to_native(self, value):
        if value is not None and self.format_key is not None:
            format_string = get_format(self.format_key)
            format = datetime_format_js2py(format_string)
            return value.strftime(format)
        return super(BaseL10NField, self).to_native(value)


class DateL10nField(BaseL10NField, DateField):
    format_key = 'COSINNUS_DATETIMEPICKER_DATE_FORMAT'


class DateTimeL10nField(BaseL10NField, DateTimeField):
    format_key = 'COSINNUS_DATETIMEPICKER_DATETIME_FORMAT'


class TimeL10nField(BaseL10NField, TimeField):
    format_key = 'COSINNUS_DATETIMEPICKER_TIME_FORMAT'
