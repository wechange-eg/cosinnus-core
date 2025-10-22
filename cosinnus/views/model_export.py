# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.conf import settings
from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView, View

from cosinnus.utils.functions import resolve_class
from cosinnus.utils.http import make_csv_response, make_xlsx_response
from cosinnus.views.mixins.group import RequireSuperuserMixin

logger = logging.getLogger('cosinnus')

CONFIG = settings.COSINNUS_MODEL_EXPORTERS


class CosinnusModelExportView(RequireSuperuserMixin, TemplateView):
    http_method_names = ['get', 'post']
    template_name = 'cosinnus/model_export/model_export.html'

    redirect_view = None
    export_title = None
    export_processor = None
    export_state = None

    def init_export_config(self, slug):
        self.redirect_view = reverse_lazy('cosinnus:administration-model-export', args=[slug])
        self.export_title = CONFIG[slug]['title']
        self.export_processor = resolve_class(CONFIG[slug]['classpath'])()
        self.export_state = self.export_processor.get_state()

    def get(self, request, *args, **kwargs):
        self.init_export_config(kwargs['slug'])
        return super(CosinnusModelExportView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.init_export_config(kwargs['slug'])
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
        context = super(CosinnusModelExportView, self).get_context_data(**kwargs)
        context.update(
            {
                'export_title': self.export_title,
                'export_state': self.export_state,
                'export_timestamp': self.export_processor.get_current_export_timestamp(),
            }
        )
        return context


model_export_view = CosinnusModelExportView.as_view()


class CosinnusModelExportDownloadBaseView(RequireSuperuserMixin, View):
    http_method_names = ['get']
    export_processor = None
    export_response_function = None

    def get(self, request, *args, **kwargs):
        slug = kwargs['slug']
        self.export_processor = resolve_class(CONFIG[slug]['classpath'])()
        data = self.export_processor.get_current_export_csv()
        if not data:
            raise Http404
        header = self.export_processor.get_header()
        filename = f'{slug} export'
        response = self.__class__.export_response_function(data, header, filename)
        return response


class CosinnusModelExportCSVDownloadView(CosinnusModelExportDownloadBaseView):
    export_response_function = make_csv_response


model_export_csv_download_view = CosinnusModelExportCSVDownloadView.as_view()


class CosinnusModelExportXLSXDownloadView(CosinnusModelExportDownloadBaseView):
    export_response_function = make_xlsx_response


model_export_xlsx_download_view = CosinnusModelExportXLSXDownloadView.as_view()
