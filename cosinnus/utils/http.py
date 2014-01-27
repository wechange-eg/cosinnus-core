# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json
import csv
import codecs
import six

from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse

from cosinnus.conf import settings


__all__ = ('JSONResponse', 'CSVResponse')


# Taken from bakery: https://github.com/muffins-on-dope/bakery
# License: BSD
# https://github.com/muffins-on-dope/bakery/blob/9bd3b6b93b/bakery/api/views.py
DUMPS_KWARGS = {
    'cls': DjangoJSONEncoder,
    'indent': True if settings.DEBUG else None
}


class JSONResponse(HttpResponse):

    def __init__(self, data):
        super(JSONResponse, self).__init__(
            json.dumps(data, **DUMPS_KWARGS),
            content_type='application/json'
        )


class UnicodeWriter:
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
