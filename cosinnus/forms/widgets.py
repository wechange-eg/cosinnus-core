# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.formats import get_format
from django.utils.translation import get_language

from bootstrap3_datetime.widgets import DateTimePicker

from cosinnus.utils.dates import datetime_format_js2py
from django.forms.widgets import SplitDateTimeWidget


class BaseL10NPicker(DateTimePicker):
    js_format_key = None

    def render(self, name, value, attrs=None):
        if self.js_format_key is not None and self.options:
            js_format_string = get_format(self.js_format_key)
            self.options.update({
                'format': js_format_string,
                'language': get_language(),
            })
            self.format = datetime_format_js2py(js_format_string)
        return super(BaseL10NPicker, self).render(name=name, value=value, attrs=attrs)

    def _format_value(self, value):
        js_format = self.options.get('format')
        self.format = datetime_format_js2py(js_format)
        return super(BaseL10NPicker, self)._format_value(value)


class DateTimeL10nPicker(BaseL10NPicker):
    js_format_key = 'COSINNUS_DATETIMEPICKER_DATETIME_FORMAT'


class DateL10nPicker(BaseL10NPicker):
    js_format_key = 'COSINNUS_DATETIMEPICKER_DATE_FORMAT'


class TimeL10nPicker(BaseL10NPicker):
    js_format_key = 'COSINNUS_DATETIMEPICKER_TIME_FORMAT'
    
    
class SplitHiddenDateWidget(SplitDateTimeWidget):
    """
    A Widget that splits datetime input into a hidden date input and a shown time input.
    """
    is_hidden = True

    def __init__(self, attrs=None, date_format=None, time_format=None):
        super(SplitHiddenDateWidget, self).__init__(attrs, date_format, time_format)
        self.widgets[0].input_type = 'hidden'
        self.widgets[0].is_hidden = True
