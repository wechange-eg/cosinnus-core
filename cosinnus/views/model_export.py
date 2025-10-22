# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from typing import Optional

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils import translation
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView, View

from cosinnus.utils.functions import resolve_class
from cosinnus.utils.http import make_csv_response, make_xlsx_response
from cosinnus.views.mixins.group import RequireSuperuserMixin

logger = logging.getLogger('cosinnus')

# config is initialized below
# CONFIG = {
#     'slug': {'title': title-string, 'exporter': export-processor-instance},
#     ...
# }
CONFIG = None


def _init_config() -> Optional[dict]:
    if CONFIG is not None:
        raise ImproperlyConfigured('Already configured, init should only be called once')

    if not getattr(settings, 'COSINNUS_MODEL_EXPORT_ADMINISTRATION_VIEWS_ENABLED', False):
        return None

    config_items = getattr(settings, 'COSINNUS_MODEL_EXPORTERS', {}).items()
    if not config_items:
        raise ImproperlyConfigured('No ModelExporters configured')

    config_validated = {}
    for slug, exporter_conf in config_items:
        try:
            exporter_instance = resolve_class(exporter_conf['classpath'])()
            config_validated[slug] = {'title': exporter_conf['title'], 'exporter': exporter_instance}
        except Exception as e:
            raise ImproperlyConfigured('Error initializing exporter "%s"' % slug) from e

    return config_validated


class CosinnusModelExportView(RequireSuperuserMixin, TemplateView):
    http_method_names = ['get', 'post']
    template_name = 'cosinnus/model_export/model_export.html'

    redirect_view = None
    export_title = None
    export_processor = None
    export_state = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        slug = kwargs['slug']
        try:
            config = CONFIG[slug]
        except KeyError:
            raise Http404()

        self.redirect_view = reverse_lazy('cosinnus:administration-model-export', args=[slug])
        self.export_title = config['title']
        self.export_processor = config['exporter']
        self.export_state = self.export_processor.get_state()

    def post(self, request, *args, **kwargs):
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
        context = super().get_context_data(**kwargs)
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
    filename = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        slug = kwargs['slug']
        try:
            config = CONFIG[slug]
        except KeyError:
            raise Http404()

        self.export_processor = config['exporter']
        # use base-language for filename generation to ensure a pretty slugify result
        with translation.override(None):
            self.filename = str(slugify(config['title']))

    def get(self, request, *args, **kwargs):
        data = self.export_processor.get_current_export_csv()
        if not data:
            raise Http404
        header = self.export_processor.get_header()
        response = self.__class__.export_response_function(data, header, self.filename)
        return response


class CosinnusModelExportCSVDownloadView(CosinnusModelExportDownloadBaseView):
    export_response_function = make_csv_response


model_export_csv_download_view = CosinnusModelExportCSVDownloadView.as_view()


class CosinnusModelExportXLSXDownloadView(CosinnusModelExportDownloadBaseView):
    export_response_function = make_xlsx_response


model_export_xlsx_download_view = CosinnusModelExportXLSXDownloadView.as_view()

# initialize config on import
# noinspection PyRedeclaration
CONFIG = _init_config()
