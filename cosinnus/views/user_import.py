# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.urls.base import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import TemplateView
from django.views.generic.detail import DetailView
from django.views.generic.edit import DeleteView
from django.views.generic.list import ListView

from cosinnus.conf import settings
from cosinnus.forms.user_import import CosinusUserImportCSVForm
from cosinnus.models.user_import import CosinnusUserImport, CosinnusUserImportProcessor
from cosinnus.views.mixins.group import RequireSuperuserMixin

logger = logging.getLogger('cosinnus')


class ArchivedCosinnusUserImportListView(RequireSuperuserMixin, ListView):
    model = CosinnusUserImport
    template_name = 'cosinnus/user_import/user_import_archived_list.html'

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(state=CosinnusUserImport.STATE_ARCHIVED)


archived_user_import_list_view = ArchivedCosinnusUserImportListView.as_view()


class ArchivedCosinnusUserImportDetailView(RequireSuperuserMixin, DetailView):
    model = CosinnusUserImport
    template_name = 'cosinnus/user_import/user_import_archived_detail.html'


archived_user_import_detail_view = ArchivedCosinnusUserImportDetailView.as_view()


class ArchivedCosinnusUserImportDeleteView(RequireSuperuserMixin, DeleteView):
    model = CosinnusUserImport
    message_success = _('The Archived User Import Entry was deleted successfully.')

    def get_success_url(self):
        messages.success(self.request, self.message_success)
        return reverse('cosinnus:administration-archived-user-import-list')


archived_user_import_delete_view = ArchivedCosinnusUserImportDeleteView.as_view()


class CosinnusUserImportView(RequireSuperuserMixin, TemplateView):
    http_method_names = ['get', 'post']
    template_name = 'cosinnus/user_import/user_import_form.html'
    redirect_view = reverse_lazy('cosinnus:administration-user-import')

    def get_current_import_object(self):
        self.import_object = None
        objects = CosinnusUserImport.objects.exclude(state=CosinnusUserImport.STATE_ARCHIVED)
        if objects.count() > 0:
            if objects.count() > 1:
                logger.warn(
                    'CosinnusUserImport: Accessed the import form with more than 1 import object of non-archived state present!'
                )
                if settings.DEBUG:
                    raise Exception('Too many Import objects!')
            self.import_object = objects[0]
        return self.import_object

    def redirect_with_error(self, message=None):
        message = message or _('This action is not allowed right now')
        messages.error(self.request, message + ': ' + self.action)
        return redirect(self.redirect_view)

    def set_form_view(self):
        self.form_view = None
        if not self.import_object:
            self.form_view = 'upload'
        else:
            if self.import_object.state == CosinnusUserImport.STATE_DRY_RUN_RUNNING:
                self.form_view = 'dry-run-running'
            if self.import_object.state == CosinnusUserImport.STATE_IMPORT_RUNNING:
                self.form_view = 'import-running'
            elif self.import_object.state == CosinnusUserImport.STATE_DRY_RUN_FINISHED_INVALID:
                self.form_view = 'invalid'
            elif self.import_object.state == CosinnusUserImport.STATE_DRY_RUN_FINISHED_VALID:
                self.form_view = 'import-ready'
            elif self.import_object.state == CosinnusUserImport.STATE_IMPORT_FINISHED:
                self.form_view = 'finished'
            elif self.import_object.state == CosinnusUserImport.STATE_IMPORT_FAILED:
                self.form_view = 'failed'

    def get(self, request, *args, **kwargs):
        self.get_current_import_object()
        self.set_form_view()
        return super(CosinnusUserImportView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.get_current_import_object()
        self.set_form_view()
        self.action = self.request.POST.get('action', None)
        # csv = self.request.POST.get()
        # do stuff

        # disallowed states
        if self.import_object and self.import_object.state in [
            CosinnusUserImport.STATE_DRY_RUN_RUNNING,
            CosinnusUserImport.STATE_IMPORT_RUNNING,
        ]:
            return self.redirect_with_error(_('Another import is currently running!'))

        if self.action == 'upload':
            # POST upload, can only do this when no current import exists
            if self.import_object:
                return self.redirect_with_error()
            upload_response = self.do_csv_upload()
            if upload_response:
                return upload_response
        elif self.action == 'import':
            # POST import, requires a valid dry run import object to exist
            if (
                not self.import_object
                or not self.import_object.state == CosinnusUserImport.STATE_DRY_RUN_FINISHED_VALID
            ):
                return self.redirect_with_error(_('No validated CSV upload found to start the import from!'))
            self.do_start_import_from_dryrun(self.import_object)
        elif self.action == 'archive':
            if not self.import_object or not self.import_object.state == CosinnusUserImport.STATE_IMPORT_FINISHED:
                return self.redirect_with_error()
            self.do_archive_import(self.import_object)
            return redirect(self.redirect_view)
        elif self.action == 'scrap':
            if not self.import_object or self.import_object.state not in [
                CosinnusUserImport.STATE_DRY_RUN_FINISHED_INVALID,
                CosinnusUserImport.STATE_DRY_RUN_FINISHED_VALID,
                CosinnusUserImport.STATE_IMPORT_FAILED,
            ]:
                return self.redirect_with_error()
            self.import_object.delete()
        else:
            return self.redirect_with_error(_('Unknown POST action!'))
        return redirect(self.redirect_view)

    def do_csv_upload(self):
        """Returns a HTTPResponse if errrors, None otherwise"""
        # parse csv in form
        form = CosinusUserImportCSVForm(files=self.request.FILES)
        setattr(self, 'form', form)
        if form.is_valid():
            csv_data = form.cleaned_data.get('csv')
            ignored_columns = csv_data['ignored_columns']

            import_object = CosinnusUserImport(
                creator=self.request.user,
                state=CosinnusUserImport.STATE_DRY_RUN_RUNNING,
                import_data=csv_data['data_dict_list'],
            )
            if ignored_columns:
                import_object.append_to_report(
                    str(
                        _('The following columns were not recognized and were ignored')
                        + ' "'
                        + '", "'.join(ignored_columns)
                    )
                    + '"',
                    'warning',
                )
            import_object.save()
            # start-dry-run threaded
            CosinnusUserImportProcessor().do_import(import_object, dry_run=True, import_creator=self.request.user)
        else:
            return self.render_to_response(self.get_context_data())

    def do_start_import_from_dryrun(self, import_object):
        # start import threaded from the object
        import_object.clear_report()
        CosinnusUserImportProcessor().do_import(import_object, dry_run=False, import_creator=self.request.user)

    def do_archive_import(self, import_object):
        before_last_modified = import_object.last_modified
        import_object.state = CosinnusUserImport.STATE_ARCHIVED
        import_object.save()
        # force previous timestamp
        CosinnusUserImport.objects.filter(pk=import_object.pk).update(last_modified=before_last_modified)
        messages.success(self.request, _('The import was successfully archived.'))

    def get_context_data(self, **kwargs):
        context = super(CosinnusUserImportView, self).get_context_data(**kwargs)
        context.update(
            {
                'object': self.import_object,
                'progress_string': self.import_object.get_import_progress_cache() if self.import_object else None,
                'form_view': self.form_view,
                'required_columns': ','.join(CosinnusUserImportProcessor.KNOWN_CSV_IMPORT_COLUMNS_HEADERS),
                'form': getattr(self, 'form', CosinusUserImportCSVForm()),
            }
        )
        return context


user_import_view = CosinnusUserImportView.as_view()
