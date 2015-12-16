# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import csv
import codecs
from django.db import transaction

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, delimiter=b',', quotechar=b'"', **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self


def csv_import_projects(csv_file, delimiter=b';'):
    """ Imports CosinnusGroups (projects and societies) from a CSV file (InMemory or opened).
        
        @return: (imported_groups, imported_projects, updated_groups, updated_projects): 
             a 4-tuple of groups and projects imported and groups and projects updated 
        @raise UnicodeDecodeError: if the supplied csv_file is not encoded in 'utf-8' """
    
    rows = UnicodeReader(csv_file)
    debug = ''
    
    # rollback DB on error
    with transaction.atomic():
        
        for row in rows:
            # TODO: import projects from rows
            debug += ' | '.join(row) + ' ---- '
            
        
    return ([], [], [], [], debug)


def import_from_settings(name):
    from django.core.exceptions import ImproperlyConfigured
    from django.utils.importlib import import_module
    from cosinnus.conf import settings

    try:
        value = getattr(settings, name, None)
        module_name, _, klass_name = value.rpartition('.')
    except ValueError:
        raise ImproperlyConfigured("%s must be of the form 'path.to.MyClass'" %
                                   name)
    module = import_module(module_name)
    klass = getattr(module, klass_name, None)
    if klass is None:
        raise ImproperlyConfigured("%s does not exist." % klass_name)
    return klass
