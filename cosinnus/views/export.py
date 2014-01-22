# -*- coding: utf-8 -*-
from __future__ import unicode_literals

"""
Export views to be used by cosinnus apps
"""

from django.core.exceptions import ImproperlyConfigured
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from django.views.generic import View

from cosinnus.utils.http import JSONResponse
from cosinnus.views.mixins.group import RequireAdminMixin


class JSONExportView(RequireAdminMixin, View):
    """
    View to return a JSON document which contains an app's model data on
    GET requests. Requires the user to have admin rights (on the current group)
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
        super(JSONExportView, self).__init__(*args, **kwargs)

    def get_data(self):
        data = {
            'group': self.group.name,
            'fields': ['id', 'title'] + self.fields,
            'rows': [],
        }

        # optimisation to not recalculate display funcnames for each object
        display_funcnames = {}
        for field in self.fields:
            display_funcnames[field] = 'get_%s_display' % field

        for obj in self.model.objects.filter(group=self.group).order_by('pk'):
            row = [str(obj.pk), obj.title]
            for field in self.fields:
                try:
                    # careful: returns a callable
                    value = getattr(obj, display_funcnames[field])()
                except AttributeError:
                    value = getattr(obj, field, '')
                row.append(str(value))
            data['rows'].append(row)
        return data

    def get(self, request, *args, **kwargs):
        data = self.get_data()
        response = JSONResponse(data)
        filename = '%s.%s.%s.json' % (
            self.file_prefix, self.group.slug, now().strftime('%Y%m%d%H%M%S'))
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename
        return response
