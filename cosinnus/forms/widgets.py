# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from bootstrap3_datetime.widgets import DateTimePicker
from django.forms import widgets
from django.forms.widgets import DateInput, SplitDateTimeWidget, TimeInput
from django.utils.translation import get_language

from cosinnus.utils.dates import datetime_format_js2py
from cosinnus.utils.lanugages import get_format_safe


def _is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


class BaseL10NPicker(DateTimePicker):
    js_format_key = None

    def render(self, name, value, attrs=None, renderer=None):
        if self.js_format_key is not None and self.options:
            js_format_string = get_format_safe(self.js_format_key)
            self.options.update(
                {
                    'format': js_format_string,
                    'language': get_language(),
                }
            )
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
    """TimeInput widget that allows very freeform time input and assumes sensible times:
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
                return raw_time + ':00'
            if len(raw_time) <= 4:
                return raw_time[:-2] + ':' + raw_time[-2:]
        return super(EasyFormatTimeInput, self).value_from_datadict(data, files, name)


class CosinnusSplitDateTimeWidget(SplitDateTimeWidget):
    """
    A Widget that splits datetime input into two <input type="text"> boxes.

    Use like this: `forms.SplitDateTimeField(widget=SplitHiddenDateWidget(default_time='00:00'))`
    """

    default_time = None

    def __init__(self, attrs=None, date_format=None, time_format=None, default_time=None):
        widgets = (DateInput(attrs=attrs, format=date_format), EasyFormatTimeInput(attrs=attrs, format=time_format))
        self.default_time = default_time
        super(SplitDateTimeWidget, self).__init__(widgets, attrs)

    def value_from_datadict(self, data, files, name):
        """If no time value is given, patch in the default time if it is given"""
        date_name = '%s_0' % name
        time_name = '%s_1' % name
        # set a default time if a date is set
        if self.default_time and data.get(date_name) and not data.get(time_name):
            data._mutable = True
            data[time_name] = self.default_time
        return super(CosinnusSplitDateTimeWidget, self).value_from_datadict(data, files, name)


class SplitHiddenDateWidget(CosinnusSplitDateTimeWidget):
    """
    A Widget that splits datetime input into a hidden date input and a shown time input.
    """

    is_hidden = True

    def __init__(self, attrs=None, date_format=None, time_format=None, default_time=None):
        super(SplitHiddenDateWidget, self).__init__(attrs, date_format, time_format, default_time=default_time)
        self.widgets[0].input_type = 'hidden'


class PrettyJSONWidget(widgets.Textarea):
    """A pretty-printed JSON widget.
    From https://stackoverflow.com/a/52627264/1407929"""

    def format_value(self, value):
        try:
            value = json.dumps(json.loads(value), indent=4, sort_keys=True)
            # these lines will try to adjust size of TextArea to fit to content
            row_lengths = [len(r) for r in value.split('\n')]
            self.attrs['rows'] = min(max(len(row_lengths) + 4, 10), 30)
            self.attrs['cols'] = min(max(max(row_lengths) + 4, 40), 120)
            return value
        except Exception:
            return super(PrettyJSONWidget, self).format_value(value)
