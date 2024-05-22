# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView, View

from cosinnus.models.user_export import CosinnusUserExportProcessor
from cosinnus.utils.http import make_csv_response, make_xlsx_response
from cosinnus.views.mixins.group import RequireSuperuserMixin

logger = logging.getLogger('cosinnus')


class CosinnusUserExportView(RequireSuperuserMixin, TemplateView):
    http_method_names = ['get', 'post']
    template_name = 'cosinnus/user_export/user_export.html'
    redirect_view = reverse_lazy('cosinnus:administration-user-export')

    export_processor = CosinnusUserExportProcessor()
    export_state = None

    def set_export_state(self):
        self.export_state = self.export_processor.get_state()

    def get(self, request, *args, **kwargs):
        self.set_export_state()
        return super(CosinnusUserExportView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.set_export_state()
        action = self.request.POST.get('action', None)

        # post not allowed while export is running
        if self.export_state == self.export_processor.STATE_EXPORT_RUNNING:
            messages.error(self.request, _('Another export is currently running!'))
            return redirect(self.redirect_view)

        if action == 'start':
            self.export_processor.do_export()
        elif action == 'delete':
            self.export_processor.delete_export()

        return redirect(self.redirect_view)

    def get_context_data(self, **kwargs):
        context = super(CosinnusUserExportView, self).get_context_data(**kwargs)
        context.update(
            {
                'export_state': self.export_state,
                'export_timestamp': self.export_processor.get_current_export_timestamp(),
            }
        )
        return context


user_export_view = CosinnusUserExportView.as_view()


class CosinnusUserExportDownloadBaseView(RequireSuperuserMixin, View):
    http_method_names = ['get']
    export_processor = CosinnusUserExportProcessor()
    export_response_function = None

    def get(self, request, *args, **kwargs):
        data = self.export_processor.get_current_export_csv()
        if not data:
            raise Http404
        header = self.export_processor.get_header()
        filename = self.export_processor.get_filename()
        response = self.__class__.export_response_function(data, header, filename)
        return response


class CosinnusUserExportCSVDownloadView(CosinnusUserExportDownloadBaseView):
    export_response_function = make_csv_response


user_export_csv_download_view = CosinnusUserExportCSVDownloadView.as_view()


class CosinnusUserExportXLSXDownloadView(CosinnusUserExportDownloadBaseView):
    export_response_function = make_xlsx_response


user_export_xlsx_download_view = CosinnusUserExportXLSXDownloadView.as_view()
