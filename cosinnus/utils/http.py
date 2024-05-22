# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import codecs
import csv
import json
from builtins import object
from urllib.parse import urlparse, urlunparse

import six
import xlsxwriter
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse, QueryDict
from django.utils.timezone import now

from cosinnus.conf import settings

__all__ = ('JSONResponse', 'CSVResponse')


# Taken from bakery: https://github.com/muffins-on-dope/bakery
# License: BSD
# https://github.com/muffins-on-dope/bakery/blob/9bd3b6b93b/bakery/api/views.py
DUMPS_KWARGS = {'cls': DjangoJSONEncoder, 'indent': True if settings.DEBUG else None}


class JSONResponse(HttpResponse):
    def __init__(self, data, status=200, content_type='application/json', **kwargs):
        """
        Create a new HTTP response which content_type defaults to
        ``'application/json'``.

        :param data: Any data type the
            :class:`~django.core.serializers.json.DjangoJSONEncoder` can
            handle (unless a different class is defined).
        :param int status: The HTTP response code. (Defaults to 200)
        :param str content_type: The content type for the response. (Defaults
            to ``'application/json'``)
        :param kwargs: Any additional kwargs are passed to the ``json.dumps``
            call.
        """
        ekwargs = {}
        ekwargs.update(DUMPS_KWARGS)
        dump = json.dumps(data, **ekwargs)
        super(JSONResponse, self).__init__(content=dump, status=status, content_type=content_type)


class UnicodeWriter(object):
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding='utf-8', **kwds):
        # Redirect output to a queue
        self.queue = six.moves.cStringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode('utf-8') for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode('utf-8')
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


class CSVResponse(HttpResponse):
    def __init__(self):
        super(CSVResponse, self).__init__(content_type='text/csv')

    def writerows(self, rows, fieldnames=[]):
        # can't have this in constructor, coz csv module needs initialised file
        # (response) object to write to
        if six.PY2:
            writer = UnicodeWriter(self)
        else:
            writer = csv.writer(self)

        if fieldnames:
            writer.writerow(fieldnames)
        writer.writerows(rows)


def make_csv_response(rows, row_names=[], file_name=None):
    """
    Shortcut to turn a list of rows into a quick CSV download response.
    """
    response = CSVResponse()
    response.writerows(rows, fieldnames=row_names)
    filename = '%s - %s.csv' % (file_name or 'export', now().strftime('%Y%m%d %H%M%S'))
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    return response


def make_xlsx_response(rows, row_names=[], file_name=None):
    """
    Shortcut to turn a list of rows into a quick XLSX download response.
    """
    filename = '%s - %s.xlsx' % (file_name or 'export', now().strftime('%Y%m%d %H%M%S'))
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument' '.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    workbook = xlsxwriter.Workbook(response, {'in_memory': True, 'strings_to_formulas': False, 'remove_timezone': True})
    worksheet = workbook.add_worksheet()

    row = 0
    col = 0
    if row_names:
        for item in row_names:
            worksheet.write(row, col, str(item))
            col += 1
        row += 1
        col = 0

    for table_row in rows:
        for cell in table_row:
            worksheet.write(row, col, str(cell))
            col += 1
        row += 1
        col = 0

    workbook.close()
    return response


def add_url_param(url, param_key, param_value):
    """Given a full URL, this returns the same url with the given GET parameter added,
    or the parameter's value replaced if present."""
    parsed = urlparse(url)
    query = parsed.query
    dic = QueryDict(query)
    dic._mutable = True
    dic[param_key] = param_value
    query = dic.urlencode()
    url = urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, query, parsed.fragment))
    return url


def remove_url_param(url, param_key=None, param_value=None):
    """Given a full URL, this returns the same url without the given GET parameter, if present.
    If a `param_value` is given, will only remove the param if `param_value` matches its value.
    If no `param_key` is given, will remove *all* params."""
    parsed = urlparse(url)
    query = parsed.query
    dic = QueryDict(query)
    dic._mutable = True
    if dic.get(param_key, None) and (param_value is None or dic.get(param_key, None) == param_value):
        del dic[param_key]
        query = dic.urlencode()
    url = urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, query if param_key else '', parsed.fragment)
    )
    return url


def is_ajax(request):
    """
    Checks if the request is an ajax request.
    Copy of the deprecated Django request attribute.
    Deprecation note: method is deprecated as it relied on a jQuery-specific way of signifying AJAX calls, while current
    usage tends to use the JavaScript Fetch API.
    """
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
