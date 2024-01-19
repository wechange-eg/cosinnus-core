# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
import requests
import six
import sys

from cosinnus.views.mixins.hierarchy import HierarchicalListCreateViewMixin
from cosinnus.views.mixins.filters import CosinnusFilterMixin
from cosinnus_etherpad.filters import EtherpadFilter
from cosinnus.utils.urls import group_aware_reverse
from urllib.error import HTTPError, URLError
from django.shortcuts import redirect
from django.http.response import HttpResponse, Http404
from cosinnus.views.attached_object import AttachableViewMixin
from django.utils.encoding import force_text
from django.utils.timezone import now
from cosinnus.views.common import DeleteElementView
from django.core.exceptions import ImproperlyConfigured

try:
    from urllib.parse import urlparse
except ImportError:
    from urllib.parse import urlparse
import logging

from django.contrib import messages
from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from django.views.generic import DetailView, RedirectView
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from cosinnus_etherpad.utils.etherpad_client import EtherpadException

from cosinnus.views.hierarchy import AddContainerView, MoveElementView
from cosinnus.views.mixins.group import (
    RequireReadMixin, RequireWriteMixin, FilterGroupMixin, GroupFormKwargsMixin,
    RequireReadWriteHybridMixin, RequireLoggedInMixin)
from cosinnus.views.mixins.tagged import (HierarchyTreeMixin,
    HierarchyPathMixin, HierarchyDeleteMixin, RecordLastVisitedMixin)
from cosinnus.views.mixins.user import UserFormKwargsMixin

from cosinnus_etherpad.conf import settings
from cosinnus_etherpad.models import Etherpad, EtherpadNotSupportedByType,\
    Ethercalc, TYPE_ETHERCALC
from cosinnus_etherpad.forms import EtherpadForm

if 'cosinnus_document' in settings.INSTALLED_APPS:
    from cosinnus_document.models import Document

if 'cosinnus_file' in settings.INSTALLED_APPS:
    from django.core.files.base import ContentFile
    from cosinnus_file.models import FileEntry

logger = logging.getLogger('cosinnus')



def _get_cookie_domain():
    domain = urlparse(settings.COSINNUS_ETHERPAD_BASE_URL).netloc

    # strip the port (if exists)
    domain = domain.split(':')[0]

    # strip the hostname
    split_domain = domain.split('.')
    # only if we have at least 2 dots use the split domain
    # http://curl.haxx.se/rfc/cookie_spec.html
    if len(split_domain) > 2:
        domain = '.' + '.'.join(split_domain[1:])
    else:
        domain = None
    return domain


class EtherpadIndexView(RequireReadMixin, RedirectView):
    permanent = False

    def get_redirect_url(self, **kwargs):
        return group_aware_reverse('cosinnus:etherpad:list',
                       kwargs={'group': self.group})

index_view = EtherpadIndexView.as_view()


class EtherpadListView(RequireReadMixin, FilterGroupMixin,
                     HierarchyTreeMixin, ListView):
    model = Etherpad

    def get(self, request, *args, **kwargs):
        self.sort_fields_aliases = self.model.SORT_FIELDS_ALIASES
        return super(EtherpadListView, self).get(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(EtherpadListView, self).get_context_data(**kwargs)
        tree = self.get_tree(self.object_list)
        context.update({'tree': tree})
        return context

list_view = EtherpadListView.as_view()


class EtherpadDetailView(RequireReadMixin, RecordLastVisitedMixin, FilterGroupMixin, DetailView):
    model = Etherpad
    template_name = 'cosinnus_etherpad/etherpad_detail.html'
    
    def get_context_data(self, *args, **kwargs):
        ctx = super(EtherpadDetailView, self).get_context_data(*args, **kwargs)
        ctx.update({
            'etherpad': ctx['object'],
        })
        return ctx
    
    def render_to_response(self, context, **response_kwargs):
        if 'cosinnus_document' in settings.INSTALLED_APPS:
            context['has_document'] = True
        if 'cosinnus_file' in settings.INSTALLED_APPS:
            context['has_file'] = True

        response = super(EtherpadDetailView, self).render_to_response(
            context, **response_kwargs)

        # set cross-domain session cookie for etherpad app
        etherpad = context['object']
        try:
            user_session_id = etherpad.get_user_session_id(self.request.user)
            domain = _get_cookie_domain()
            if domain:
                server_name = self.request.META['SERVER_NAME']
                if domain not in server_name and server_name not in domain and server_name != '127.0.0.1':
                    # this may be a problem for cross-domain access of etherpad
                    logging.warning('SERVER_NAME %s and cookie domain %s don\'t match. Setting a third-party cookie might not work!' % (server_name, domain))
            response.set_cookie('sessionID', user_session_id, domain=domain)
        except (HTTPError, EtherpadException, URLError) as exc:
            logger.error('Cosinnus Etherpad DetailView configuration error: Etherpad error', extra={'exception': exc, 'url': self.request.META.get('HTTP_REFERER', 'N/A')})
            messages.error(self.request, _('The document can not be accessed because the etherpad server could not be reached. Please contact an administrator!'))
        except EtherpadNotSupportedByType:
            pass
        
        return response

pad_detail_view = EtherpadDetailView.as_view()


class EtherpadWriteView(RequireLoggedInMixin, EtherpadDetailView):
    template_name = 'cosinnus_etherpad/etherpad_write.html'
    
    def dispatch(self, request, *args, **kwargs):
        # redirect guest users to read-only view unless soft edits are enabled
        if request.user.is_guest and not settings.COSINNUS_USER_GUEST_ACCOUNTS_ENABLE_SOFT_EDITS:
            messages.info(request, _('Editing is not permitted for guest accounts.'))
            return redirect(group_aware_reverse('cosinnus:etherpad:pad-detail', kwargs=kwargs))
        return super().dispatch(request, *args, **kwargs)
    
    def render_to_response(self, context, **response_kwargs):   
        """ Do not allow write access to pads owned by deactivated users.
            Also save last accessed on access """
        if settings.COSINNUS_LOCK_ETHERPAD_WRITE_MODE_ON_CREATOR_DELETE and not self.object.creator.is_active:
            kwargs = {'group': self.object.group, 'slug': self.object.slug}
            return redirect(group_aware_reverse('cosinnus:etherpad:pad-detail', kwargs=kwargs))
        
        response = super(EtherpadWriteView, self).render_to_response(context, **response_kwargs)
        
        try:
            self.object.last_accessed = now()
            self.object.save(update_fields=['last_accessed'])
        except Exception as e:
            extra = {'exception': force_text(e), 'user': self.request.user}
            logger.error('Error when trying to set last_accessed', extra=extra)
        return response

pad_write_view = EtherpadWriteView.as_view()


class EtherpadFormMixin(FilterGroupMixin,
                        GroupFormKwargsMixin, UserFormKwargsMixin):
    form_class = EtherpadForm
    model = Etherpad
    message_success = _('Etherpad "%(title)s" was edited successfully.')
    message_error = _('Etherpad "%(title)s" could not be edited.')

    def get_context_data(self, **kwargs):
        context = super(EtherpadFormMixin, self).get_context_data(**kwargs)
        context.update({
            'form_view': self.form_view,
        })
        if 'cosinnus_document' in settings.INSTALLED_APPS:
            context['has_document'] = True
        if 'cosinnus_file' in settings.INSTALLED_APPS:
            context['has_file'] = True
        return context

    def get_success_url(self):
        return group_aware_reverse('cosinnus:etherpad:pad-write', kwargs={
            'group': self.group,
            'slug': self.object.slug,
        })

    def form_valid(self, form):
        if form.instance.pk is None:
            form.instance.creator = self.request.user

        ret = super(EtherpadFormMixin, self).form_valid(form)
        messages.success(self.request,
            self.message_success % {'title': self.object.title})
        return ret

    def form_invalid(self, form):
        ret = super(EtherpadFormMixin, self).form_invalid(form)
        if self.object:
            messages.error(self.request,
                self.message_error % {'title': self.object.title})
        return ret


class EtherpadHybridListView(RequireReadWriteHybridMixin, HierarchyPathMixin, HierarchicalListCreateViewMixin, 
                                CosinnusFilterMixin, EtherpadFormMixin, CreateView):
    
    template_name = 'cosinnus_etherpad/etherpad_list.html'
    filterset_class = EtherpadFilter
    strict_default_sort = True
    
    form_view = 'add'
    message_success = _('Etherpad "%(title)s" was added successfully.')
    message_error = _('Etherpad "%(title)s" could not be added.')

    message_success_folder = _('Folder "%(title)s" was created successfully.')
    
    def get(self, request, *args, **kwargs):
        self.sort_fields_aliases = self.model.SORT_FIELDS_ALIASES
        return super(EtherpadHybridListView, self).get(request, *args, **kwargs)
    
    def form_valid(self, form):
        # manually set the type of Etherpad or Ethercalc
        form.instance.set_pad_type(int(self.request.POST.get('etherpad_type', 0)))
        
        try:
            # only commit changes to the database iff the etherpad has been created
            sid = transaction.savepoint()
            ret = super(EtherpadHybridListView, self).form_valid(form)
            transaction.savepoint_commit(sid)
            return ret
        except (EtherpadException, URLError) as exc:
            transaction.savepoint_rollback(sid)
            if 'padName does already exist' in force_text(exc):
                msg = _('Etherpad with name "%(name)s" already exists on pad server. Please use another name.')
                messages.error(self.request, msg % {'name': form.data.get('title', '')})
                return self.form_invalid(form)
            else:
                logger.error('Cosinnus Etherpad ListView configuration error: Etherpad Misconfigured', extra={'exception': exc, 'url': self.request.META.get('HTTP_REFERER', 'N/A')})
                messages.error(self.request, _('The document could not be created because the etherpad service is misconfigured. Please contact an administrator!'))
                return self.form_invalid(form)
        except HTTPError as exc:
            logger.error('Cosinnus Etherpad ListView configuration error: Etherpad URL invalid', extra={'exception': exc, 'url': self.request.META.get('HTTP_REFERER', 'N/A')})
            messages.error(self.request, _('The document could not be created because the etherpad server could not be reached. Please contact an administrator!'))
            return self.form_invalid(form)
    
    def get_success_url(self):
        if self.object.is_container:
            messages.success(self.request,
                self.message_success_folder % {'title': self.object.title})
            return group_aware_reverse('cosinnus:etherpad:list', kwargs={
                    'group': self.group,
                    'slug': self.object.slug})
        else:
            return group_aware_reverse('cosinnus:etherpad:pad-edit', kwargs={
                    'group': self.group,
                    'slug': self.object.slug})

pad_hybrid_list_view = EtherpadHybridListView.as_view()


class EtherpadAddContainerView(AddContainerView):
    model = Etherpad
    appname = 'etherpad'

container_add_view = EtherpadAddContainerView.as_view()


class EtherpadEditView(RequireWriteMixin, EtherpadFormMixin, AttachableViewMixin, UpdateView):
    form_view = 'edit'
    template_name = 'cosinnus_etherpad/etherpad_edit.html'
    
    def get_context_data(self, *args, **kwargs):
        ctx = super(EtherpadEditView, self).get_context_data(*args, **kwargs)
        ctx.update({
            'etherpad': ctx['object'],
        })
        return ctx
    
    def render_to_response(self, context, **response_kwargs):
        response = super(EtherpadFormMixin, self).render_to_response(
            context, **response_kwargs)
        
        # set cross-domain session cookie for etherpad app
        etherpad = context['object']
        try:
            user_session_id = etherpad.get_user_session_id(self.request.user)
            domain = _get_cookie_domain()
            if domain:
                server_name = self.request.META['SERVER_NAME']
                if domain not in server_name and server_name not in domain and server_name != '127.0.0.1':
                    # this may be a problem for cross-server therpad conections
                    logging.warning('SERVER_NAME %s and cookie domain %s don\'t match. Setting a third-party cookie might not work!' % (server_name, domain))
            response.set_cookie('sessionID', user_session_id, domain=domain)
        except (HTTPError, EtherpadException, URLError) as exc:
            logger.error('Cosinnus Etherpad EditView configuration error: Etherpad error', extra={'exception': exc, 'url': self.request.META.get('HTTP_REFERER', 'N/A')})
            messages.error(self.request, _('The document can not be accessed because the etherpad server could not be reached. Please contact an administrator!'))
        except EtherpadNotSupportedByType:
            pass
        
        return response

pad_edit_view = EtherpadEditView.as_view()


class EtherpadDeleteView(RequireWriteMixin, EtherpadFormMixin, HierarchyDeleteMixin, DeleteView):
    form_view = 'delete'
    message_success = None
    message_error = None

    def get_success_url(self):
        kwargs = {'group': self.group}
        try:
            # if possible, redirect to the object's parent folder list view
            parent_folder = self.object.__class__.objects.get(is_container=True, path=self.object.path)
            kwargs.update({'slug': parent_folder.slug})
        except:
            pass
        return group_aware_reverse('cosinnus:etherpad:list', kwargs=kwargs)

pad_delete_view = EtherpadDeleteView.as_view()


class EthercalcDownloadBaseView(RequireReadMixin, FilterGroupMixin, DetailView):
    """ Downloads a CSV file from the calc server and then serves it from this URL """
    
    suffix = None # needs to be set in extending view
    model = Etherpad
    
    def get_filename_header(self, filename):
        return 'filename=%s' % filename
    
    def render_to_response(self, context, **response_kwargs):
        if not self.suffix:
            raise ImproperlyConfigured('Need to set a `suffix` for this view!')
        # download the CSV from the calc server
        # (works by just appending '.csv' to the calc URL)
        calc = self.object
        if not calc.type == TYPE_ETHERCALC:
            raise Http404
        calc_url = '%s.%s' % (self.object.get_pad_url(), self.suffix)
        resp = requests.get(calc_url, verify=False)
        if not resp.status_code == 200:
            messages.error(self.request, _('The document can not be accessed because the etherpad server could not be reached. Please contact an administrator!'))
            return redirect(group_aware_reverse('cosinnus:etherpad:pad-write', kwargs={'group': calc.group, 'slug': calc.slug}))
        content = resp.content
        
        response = HttpResponse(content)
        content_type = resp.headers['content-type']
        if not content_type is None:
            content_type = 'application/octet-stream'
        encoding = resp.encoding
        filename = '%s.%s' % (calc.slug, self.suffix)
        response['Content-Type'] = content_type
        response['Content-Length'] = len(content)
        if encoding is not None:
            response['Content-Encoding'] = encoding
            
        filename_header = self.get_filename_header(filename)
        response['Content-Disposition'] = 'attachment; ' + filename_header
        
        return response


class EthercalcCSVView(EthercalcDownloadBaseView):
    """ Downloads a CSV file from the calc server and then serves it from this URL """
    
    suffix = 'csv'
    
    def get_filename_header(self, filename):
        # To inspect details for the below code, see http://greenbytes.de/tech/tc2231/
        user_agent = self.request.META.get('HTTP_USER_AGENT', [])
        if u'WebKit' in user_agent:
            # Safari 3.0 and Chrome 2.0 accepts UTF-8 encoded string directly.
            filename_header = 'filename=%s' % filename
        elif u'MSIE' in user_agent:
            # IE does not support internationalized filename at all.
            # It can only recognize internationalized URL, so we do the trick via routing rules.
            filename_header = ''
        else:
            # For others like Firefox, we follow RFC2231 (encoding extension in HTTP headers).
            filename_header = 'filename*=UTF-8\'\'%s' % filename
        return filename_header
    
calc_csv_view = EthercalcCSVView.as_view()


class EthercalcXLSXView(EthercalcDownloadBaseView):
    """ Downloads a CSV file from the calc server and then serves it from this URL """
    
    suffix = 'xlsx'
    
calc_xlsx_view = EthercalcXLSXView.as_view()


class EtherpadArchiveMixin(RequireWriteMixin, RedirectView):
    permanent = False
    
    def get_title(self, request, pad_title):
        import time
        from django.utils.timezone import now
#        from django.utils.translation import to_locale
#        import locale
#
#        old_locale = locale.getlocale()
#        lang_code = getattr(request, 'LANGUAGE_CODE', settings.LANGUAGE_CODE)
#        lang_locale = to_locale(settings.LANGUAGE_CODE)
#        locale.setlocale(locale.LC_ALL, str(lang_locale))
#        suffix = ' ' + now().strftime('%c')
#        locale.setlocale(locale.LC_ALL, old_locale)

        suffix = ' ' + str(int(time.mktime(now().timetuple())))
        return settings.COSINNUS_ETHERPAD_PREFIX_TITLE + pad_title + suffix

    def get_redirect_url(self, **kwargs):
        return group_aware_reverse('cosinnus:etherpad:pad-detail', kwargs={
            'group': self.group,
            'slug': self.kwargs['slug'],
        })


class EtherpadArchiveDocumentView(EtherpadArchiveMixin):
    def post(self, request, *args, **kwargs):
        if 'cosinnus_document' in settings.INSTALLED_APPS:
            pad = Etherpad.objects.get(slug=kwargs['slug'], group=self.group)
            title = self.get_title(request, pad.title)
            try:
                doc = Document.objects.get(title=title, group=self.group)
            except Document.DoesNotExist:
                doc = Document(
                    title=title,
                    group=self.group,
                    created=request.user,
                    is_draft=False)
            doc.content = pad.content
            doc.save()

            msg = _('Pad has been archived as Document: <a class="alert-link" href="%(href)s">%(title)s</a>') % {
                'href': group_aware_reverse('cosinnus:document:document-detail', kwargs={
                    'group': self.group,
                    'slug': doc.slug,
                }),
                'title': title,
            }
            messages.info(request, msg)
        return super(EtherpadArchiveDocumentView, self).post(request, *args, **kwargs)

pad_archive_document = EtherpadArchiveDocumentView.as_view()


class EtherpadArchiveFileView(EtherpadArchiveMixin):
    def _create_folder(self, request, path):
        title = path[1:]

        try:  # don't use get_or_create: creator doesn't matter for get
            FileEntry.objects.get(title=title, group=self.group, isfolder=True)
        except FileEntry.DoesNotExist:
            FileEntry.objects.create(
                title=title,
                group=self.group,
                isfolder=True,
                creator=request.user,
                path=path)

    def post(self, request, *args, **kwargs):
        if 'cosinnus_file' in settings.INSTALLED_APPS:
            pad = Etherpad.objects.get(slug=kwargs['slug'], group=self.group)
            title = self.get_title(request, pad.title)
            content = ContentFile(pad.content)
            if settings.COSINNUS_ETHERPAD_FILE_PATH.startswith('/'):
                path = settings.COSINNUS_ETHERPAD_FILE_PATH
            else:
                path = '/' + settings.COSINNUS_ETHERPAD_FILE_PATH

            self._create_folder(request, path)
            try:
                entry = FileEntry.objects.get(title=title, group=self.group)
                entry.file.delete(save=False)
            except FileEntry.DoesNotExist:
                entry = FileEntry(
                    title=title,
                    group=self.group,
                    creator=request.user,
                    mimetype='text/html',
                    path=path)
                entry.save()  # let slug be calculated
            filename = entry.slug + '.html'
            entry.file.save(filename, content, save=True)

            msg = _('Pad has been archived as File entry: <a class="alert-link" href="%(href)s">%(title)s</a>') % {
                'href': group_aware_reverse('cosinnus:file:file', kwargs={
                    'group': self.group,
                    'slug': entry.slug,
                }),
                'title': title,
            }
            messages.info(request, msg)
        return super(EtherpadArchiveFileView, self).post(request, *args, **kwargs)

pad_archive_file = EtherpadArchiveFileView.as_view()


class EtherpadMoveElementView(MoveElementView):
    model = Etherpad

move_element_view = EtherpadMoveElementView.as_view()


class EtherpadDeleteElementView(DeleteElementView):
    model = Etherpad

delete_element_view = EtherpadDeleteElementView.as_view()
