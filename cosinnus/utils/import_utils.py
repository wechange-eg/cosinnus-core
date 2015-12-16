# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import csv
import codecs
from django.utils.encoding import force_text

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


def unicode_csv_reader(utf8_data, dialect=csv.excel, **kwargs):
    csv_reader = csv.reader(utf8_data, dialect=dialect, **kwargs)
    for row in csv_reader:
        try:
            yield [unicode(cell, 'utf-8') for cell in row]
        except UnicodeDecodeError:
            try:
                yield [unicode(cell, 'utf-16') for cell in row]
            except UnicodeDecodeError:
                yield [unicode(cell, 'ISO-8859-1') for cell in row]
                
                
                #yield [unicode(cell, 'latin_1') for cell in row]
                #yield [unicode(cell, 'koi8_r') for cell in row]
                #yield [unicode(cell, 'cp1252') for cell in row]
                #yield [unicode(cell, '') for cell in row]


def csv_unireader(f, encoding="utf-8"):
    for row in csv.reader(codecs.iterencode(codecs.iterdecode(f, encoding), "utf-8")):
        yield [e.decode("utf-8") for e in row]
        

def csv_import_projects(csv_file, delimiter=b';'):
    """ Imports CosinnusGroups (projects and societies) from a CSV file (InMemory or opened).
        
        @return: (imported_groups, imported_projects, updated_groups, updated_projects): 
             a 4-tuple of groups and projects imported and groups and projects updated """
    
    
    # TODO: FIXME: no matter what i do, i can't get the example .CSV file decoded right.
    # it seems to be in ANSI, but when i decode it as such (or any other way I could come
    # up with), Umlauts in the text aren't coded right. 
    # example of what's left after printing it in the template:
    # [u'Projekt-ID;Referat;Programmlinie;Titel;Login Organisation;Passwort Organisation;Login Projekt-Blog;Passwort Projekt;Tr\xe4ger 
    
    rows = csv_unireader(csv_file, 'ISO-8859-1')
    #rows = UnicodeReader(csv_file)
    #rows = unicode_csv_reader(csv_file, delimiter=delimiter, quotechar=b'"')
    #rows = csv.reader(csv_file, dialect=csv.excel, delimiter=delimiter, quotechar=b'"')
    debu = []
    for row in rows:
        #print ">>> row:", row
        debu += [force_text(row)]
        
    return ([], [], [], [], debu)


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
