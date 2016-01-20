# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import csv
import codecs
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.template.loader import render_to_string
from threading import Thread



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


class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        # always use utf-8 to encode, no matter which encoding we decoded while reading
        return self.reader.next().encode("utf-8")
    

class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """
    
    _encoding = None

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", delimiter=b',', **kwds):
        f = UTF8Recoder(f, encoding)
        self._encoding = encoding
        self.reader = csv.reader(f, dialect=dialect, delimiter=delimiter, quotechar=b'"', **kwds)

    def next(self):
        row = self.reader.next()
        # utf-8 must be used here because we use a UTF8Reader
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self



class GroupCSVImporter(Thread):
    """ Extend this class to implement the specific import function `do_group_import``! 
        Assign your new class to the setting ``COSINNUS_CSV_IMPORT_GROUP_IMPORTER`` to have it be used for the import. 
        @param group_rows: The rows of CSV imported groups. 
        @param request: Supply a request if a report summary of the import should be mailed to the user """
    
    def __init__(self, group_rows, request=None, *args, **kwargs):
        self.group_rows = group_rows
        self.request = request
        
        if self.__class__.__name__ == 'GroupCSVImporter':
            raise ImproperlyConfigured('The GroupCSVImporter needs to be extended and requires a ``do_group_import`` function to be implemented!')
        super(GroupCSVImporter, self).__init__(*args, **kwargs)
    
    def do_group_import_threaded(self):
        self.start()
    
    def run(self):
        self.do_group_import()
    
    def do_group_import(self):
        pass
    
    def _send_summary_mail(self, template, subj_template, data):
        from cosinnus.core.mail import get_common_mail_context, send_mail_or_fail
        from cosinnus.utils.context_processors import cosinnus as cosinnus_context
        
        receiver = self.request.user
        if self.request:
            context = get_common_mail_context(self.request, user=receiver)
            context.update(cosinnus_context(self.request))
        else:
            context = {} 
        context.update(data)
        subject = render_to_string(subj_template, context)
        send_mail_or_fail(receiver.email, subject, template, context)
    
    def import_finished(self, data):
        if not self.request:
            return
        self._send_summary_mail('cosinnus/mail/csv_import_summary.txt', 'cosinnus/mail/csv_import_summary_subj.txt', data)
    
    def import_failed(self, data):
        if not self.request:
            return
        self._send_summary_mail('cosinnus/mail/csv_import_failed.txt', 'cosinnus/mail/csv_import_failed_subj.txt', data)
    

class EmptyOrUnreadableCSVContent(Exception): pass
class UnexpectedNumberOfColumns(Exception): pass 

def csv_import_projects(csv_file, request=None, encoding="utf-8", delimiter=b',', expected_columns=None):
    """ Imports CosinnusGroups (projects and societies) from a CSV file (InMemory or opened).
        
        @param expected_columns: if set to an integer, each row must have this number of columns,
                                or the import is rejected
        
        @return: (imported_groups, imported_projects, updated_groups, updated_projects): 
             a 4-tuple of groups and projects imported and groups and projects updated 
        @raise UnicodeDecodeError: if the supplied csv_file is not encoded in 'utf-8' """
    
    rows = UnicodeReader(csv_file, encoding=encoding, delimiter=delimiter)
    try:
        # de-iterate to throw encoding errors if there are any
        rows = [row for row in rows]
    except UnicodeDecodeError:
        raise
    
    # sanity check, we require more than 0 rows and more than 1 column 
    # (otherwise we likely decoded with the wrong codec, or delimiter)
    if len(rows) <= 0 or len(rows[0]) <= 1:
        raise EmptyOrUnreadableCSVContent()
    
    # sanity check for expected number of columns, in EACH row
    if expected_columns:
        expected_columns = int(expected_columns)
        if any([len(row) != expected_columns for row in rows]):
            raise UnexpectedNumberOfColumns()
    
    GroupImporter = import_from_settings('COSINNUS_CSV_IMPORT_GROUP_IMPORTER')
    importer = GroupImporter(rows, request)
    importer.do_group_import_threaded()
    
    debug = ''
    for row in rows:
        # TODO: import projects from rows
        debug += ' | '.join(row) + ' --<br/><br/>-- '
        
    return debug


