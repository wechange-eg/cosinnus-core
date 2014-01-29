# -*- coding: utf-8 -*-
from __future__ import unicode_literals

"""
Export views to be used by cosinnus apps
"""

from django.core.exceptions import ImproperlyConfigured
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.views.generic import View

from cosinnus.utils.http import JSONResponse, CSVResponse
from cosinnus.views.mixins.group import RequireAdminMixin


class ExportView(RequireAdminMixin, View):
    """
    View to return an app's model data on GET requests.
    Requires the user to have admin rights on the current group
    """

    #: list of field names to be exported; each field needs to be representable as string
    fields = []

    #: model to get data from; required to be set by subclassing view
    model = None

    #: prefix of the name of the returned file, usually the app name
    file_prefix = 'cosinnus'

    def __init__(self, *args, **kwargs):
        if not self.model:
            raise ImproperlyConfigured(_('No model given to export data from.'))
        super(ExportView, self).__init__(*args, **kwargs)
        self.fields = ['id', 'title'] + self.fields

    def get_rows(self):
        """
        Retrieves the data rows from the model in a nice format.
        Is usually used by the subclass' get_response method.
        """
        rows = []
        # optimisation to not recalculate display funcnames for each object
        display_funcnames = {}
        for field in self.fields:
            display_funcnames[field] = 'get_%s_display' % field

        for obj in self.model.objects.filter(group=self.group).order_by('pk'):
            row = []
            for field in self.fields:
                try:
                    # careful: returns a callable
                    value = getattr(obj, display_funcnames[field])()
                except AttributeError:
                    value = getattr(obj, field, '')
                row.append(str(value))
            rows.append(row)
        return rows

    def get_response(self, data):
        raise NotImplementedError('Subclasses need to implement this method.')

    def get(self, request, *args, **kwargs):
        response = self.get_response()
        filename = '%s.%s.%s.%s' % (
            self.file_prefix,
            self.group.slug,
            now().strftime('%Y%m%d%H%M%S'),
            self.file_extension)
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        return response


class JSONExportView(ExportView):
    """
    Extends the ExportView to export JSON data
    """
    file_extension = 'json'

    def get_response(self):
        data = {
            'group': self.group.name,
            'fields': self.fields,
            'rows': self.get_rows(),
        }
        return JSONResponse(data)


class CSVExportView(ExportView):
    """
    Extends the ExportView to export CSV data
    """
    file_extension = 'csv'

    def get_response(self):
        rows = self.get_rows()
        response = CSVResponse()
        response.writerows(rows, fieldnames=self.fields)
        return response
