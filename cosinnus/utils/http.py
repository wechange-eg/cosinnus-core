# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
import json
import csv
import codecs
import six

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse

from cosinnus.conf import settings
from django.utils.timezone import now
import xlsxwriter


__all__ = ('JSONResponse', 'CSVResponse')


# Taken from bakery: https://github.com/muffins-on-dope/bakery
# License: BSD
# https://github.com/muffins-on-dope/bakery/blob/9bd3b6b93b/bakery/api/views.py
DUMPS_KWARGS = {
    'cls': DjangoJSONEncoder,
    'indent': True if settings.DEBUG else None
}


class JSONResponse(HttpResponse):

    def __init__(self, data, status=200, content_type='application/json',
            **kwargs):
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
        super(JSONResponse, self).__init__(
            content=dump, status=status, content_type=content_type
        )


class UnicodeWriter(object):
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = six.moves.cStringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
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
    filename = '%s - %s.csv' % (
        file_name or 'export',
        now().strftime('%Y%m%d %H%M%S'))
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename
    return response


def make_xlsx_response(rows, row_names=[], file_name=None):
    """ 
        Shortcut to turn a list of rows into a quick XLSX download response.
    """
    filename = '%s - %s.xlsx' % (
        file_name or 'export',
        now().strftime('%Y%m%d %H%M%S'))
    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument'
                     '.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename="{}"'.format(filename)
    workbook = xlsxwriter.Workbook(response, {
        'in_memory': True,
        'strings_to_formulas': False,
        'remove_timezone': True
    })
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

