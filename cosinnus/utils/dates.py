# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime

from django.template.defaultfilters import date as django_date_filter
from django.template.loader import render_to_string
from django.utils import dateformat
from django.utils.formats import date_format
from django.utils.safestring import mark_safe
from django.utils.timezone import localtime, now
from django.utils.translation import ugettext_lazy as _
import pytz


# http://momentjs.com/docs/#/parsing/string-format/
# http://docs.python.org/2/library/datetime.html#strftime-strptime-behavior
FORMAT_MAP = (
    ('DDD', r'%j'),
    ('DD', r'%d'),
    ('MMMM', r'%B'),
    ('MMM', r'%b'),
    ('MM', r'%m'),
    ('YYYY', r'%Y'),
    ('YY', r'%y'),
    ('HH', r'%H'),
    ('hh', r'%I'),
    ('mm', r'%M'),
    ('ss', r'%S'),
    ('a', r'%p'),
    ('ZZ', r'%z'),
)


def datetime_format_py2js(format):
    """
    Converts Python's :func:`~time.strftime` format to a JavaScript notation,
    eg. ``"%d"`` to ``"DD"`` or ``"%Y"`` to ``"YYYY"``.
    """
    for js, py in FORMAT_MAP:
        format = format.replace(py, js)
    return format


def datetime_format_js2py(format):
    """
    Converts a JavaScript datetime notation to Python's :func:`~time.strftime`
    format, eg. ``"DD"`` to ``"%d"`` or ``"YYYY"`` to ``"%Y"`` .
    """
    for js, py in FORMAT_MAP:
        format = format.replace(js, py)
    return format


def timestamp_from_datetime(datetime_obj=None):
    """ Creates a float timestamp from a datetime.
        @param datetime_obj: A datetime. If none is given, uses the current time instead. """
    datetime_obj = datetime_obj or datetime.today()
    return datetime_obj.timestamp()
    
    
def datetime_from_timestamp(timestamp):
    """ Creates a datetime from a float timestamp """
    return datetime.fromtimestamp(timestamp, pytz.utc)


def localize(value, format):
    if (not format) or ("FORMAT" in format):
        return date_format(localtime(value), format)
    else:
        return dateformat.format(localtime(value), format)


class HumanizedEventTimeMixin(object):
    """ Utility function mixin for any model containing a `from_date` and `to_date` datetime field. """
    
    @property
    def single_day(self):
        if not self.from_date or not self.to_date:
            return True
        return localtime(self.from_date).date() == localtime(self.to_date).date()
    
    @property
    def is_same_day(self):
        if not self.from_date or not self.to_date:
            return True
        return localtime(self.from_date).date() == localtime(self.to_date).date()
    
    @property
    def is_same_time(self):
        if not self.from_date or not self.to_date:
            return True
        return self.from_date.time() == self.to_date.time()
    
    @property
    def is_all_day(self):
        if not self.from_date or not self.to_date:
            return False
        return (localize(self.from_date, "H:i") == '00:00') and (localize(self.to_date, "H:i") == '23:59')
    
    @property
    def is_running(self):
        has_time = self.from_date and self.to_date
        running = has_time and self.from_date <= now() <= self.to_date
        return has_time and running

    @property
    def has_ended(self):
        if self.to_date:
            return self.to_date <= now()
    
    def get_date_or_now_starting_time(self):
        """ Returns a dict like {'is_date': True, 'date': <date>}
            with is_date=False date as string "Now" if the event is running, 
            else is_date=True and date as the moment-usable datetime of the from_date. """
        _now = now()
        if self.from_date and self.from_date < _now and self.to_date > _now:
            return {'is_date': False, 'date': str(_("Now"))}
        return {'is_date': True, 'date': django_date_filter(self.from_date, 'c')}
    
    def get_period(self):
        if self.single_day:
            return localize(self.from_date, "d.m.Y")
        else:
            return "%s - %s" % (localize(self.from_date, "d.m."), localize(self.to_date, "d.m.Y"))

    def get_period_with_time(self):
        if self.is_all_day:
            return self.get_period()
        if self.single_day:
            return f'{localize(self.from_date, "d.m.Y H:i")} - {localize(self.to_date, "H:i")}'
        else:
            return f'{localize(self.from_date, "d.m.Y H:i")} - {localize(self.to_date, "d.m.Y H:i")}'

    def get_humanized_event_time_html(self):
        if not self.from_date:
            return ''
        return mark_safe(render_to_string('cosinnus_event/common/humanized_event_time.html', {'event': self})).strip()
    
    
class HumanizedEventTimeObject(HumanizedEventTimeMixin):
    """ Convenience object wrapping `HumanizedEventTimeMixin` to give easy
        access to the mixin's functions when you only have two datetimes. """
    
    from_date = None
    to_date = None
    
    def __init__(self, from_date, to_date):
        # localize naive datetimes
        self.from_date = from_date
        self.to_date = to_date
    
