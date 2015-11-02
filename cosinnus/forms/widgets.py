# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.formats import get_format
from django.utils.translation import get_language

from bootstrap3_datetime.widgets import DateTimePicker

from cosinnus.utils.dates import datetime_format_js2py
from django.forms.widgets import SplitDateTimeWidget, DateInput, TimeInput


def _is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

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


class EasyFormatTimeInput(TimeInput):
    """ TimeInput widget that allows very freeform time input and assumes sensible times:
        Short numbers without colons are considered hours, longer number without colons
        are considered hours and minutes. The rest is handled through regular validation.
        Examples:
            '7' --> '7:00'
            '1730' --> '17:30'
            '132' --> '1:32' 
            '22222222' --> '22222222'
     """
    
    def value_from_datadict(self, data, files, name):
        raw_time = data[name]
        if raw_time and len(raw_time) > 0 and _is_number(raw_time):
            if len(raw_time) <= 2:
                return raw_time + ":00"
            if len(raw_time) <= 4:
                return raw_time[:-2] + ":" + raw_time[-2:]
        return super(EasyFormatTimeInput, self).value_from_datadict(data, files, name)

class CosinnusSplitDateTimeWidget(SplitDateTimeWidget):
    """
    A Widget that splits datetime input into two <input type="text"> boxes.
    """

    def __init__(self, attrs=None, date_format=None, time_format=None):
        widgets = (DateInput(attrs=attrs, format=date_format),
                   EasyFormatTimeInput(attrs=attrs, format=time_format))
        super(SplitDateTimeWidget, self).__init__(widgets, attrs)
    
class SplitHiddenDateWidget(CosinnusSplitDateTimeWidget):
    """
    A Widget that splits datetime input into a hidden date input and a shown time input.
    """
    is_hidden = True

    def __init__(self, attrs=None, date_format=None, time_format=None):
        super(SplitHiddenDateWidget, self).__init__(attrs, date_format, time_format)
        self.widgets[0].input_type = 'hidden'
