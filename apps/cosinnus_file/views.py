# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import map
import mimetypes
import json

from os.path import basename

from django.contrib import messages
from django.http import (Http404, HttpResponse, HttpResponseNotFound,
    HttpResponseRedirect, StreamingHttpResponse)
from django.utils.translation import ungettext, ugettext_lazy as _
from django.views.generic import (CreateView, DeleteView, DetailView, ListView,
    RedirectView, UpdateView)
from django.views.generic.edit import FormMixin

from cosinnus.conf import settings
from cosinnus.utils.files import create_zip_file, create_zip_from_files,\
    append_string_to_filename
from cosinnus.templatetags.cosinnus_tags import add_current_params
from cosinnus.views.mixins.group import (RequireReadMixin, RequireWriteMixin,
    FilterGroupMixin, GroupFormKwargsMixin, RequireReadWriteHybridMixin)
from cosinnus.views.mixins.tagged import HierarchyTreeMixin, HierarchyPathMixin,\
    HierarchyDeleteMixin, RecordLastVisitedMixin
from cosinnus.views.mixins.user import UserFormKwargsMixin

from cosinnus_file.forms import FileForm, FileListForm
from cosinnus_file.models import FileEntry, get_or_create_attachment_folder
from cosinnus.views.mixins.hierarchy import HierarchicalListCreateViewMixin
from cosinnus.views.mixins.filters import CosinnusFilterMixin
from cosinnus_file.filters import FileFilter
from cosinnus.utils.urls import group_aware_reverse
from cosinnus_file.utils.strings import clean_filename
from cosinnus.views.hierarchy import MoveElementView
from django.http.response import HttpResponseNotAllowed
from cosinnus.utils.http import JSONResponse
from cosinnus.core.decorators.views import get_group_for_request
from cosinnus.utils.permissions import check_group_create_objects_access,\
    check_object_read_access
from cosinnus.utils.functions import clean_single_line_text
from cosinnus.views.attached_object import build_attachment_field_result


import logging
from django.utils.datastructures import MultiValueDict
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils.text import slugify
from django.utils.crypto import get_random_string
from cosinnus.models.tagged import BaseTagObject
from cosinnus.views.common import DeleteElementView
from ajax_forms.ajax_forms import AjaxFormsCreateViewMixin
import tempfile
import os
logger = logging.getLogger('cosinnus')


mimetypes.init()


class FileFormMixin(FilterGroupMixin, GroupFormKwargsMixin,
                    UserFormKwargsMixin):
    
    def get_context_data(self, **kwargs):
        context = super(FileFormMixin, self).get_context_data(**kwargs)
        tags = FileEntry.objects.tags()
        context.update({
            'form_view': self.form_view,
            'tags': tags
        })
        return context
    
    def form_valid(self, form):
        if form.instance.pk is None:
            form.instance.creator = self.request.user
        # save/update filesize
        if form.instance.file:
            form.instance._filesize = form.instance.file.file.size
        
        # mark as is_url for a URL filetype
        if not form.instance.file and form.instance.url:
            form.instance.is_url = True
        
        ret = super(FileFormMixin, self).form_valid(form)
        
        # trigger URL downloading 
        if self.object.is_url:
            pass # TODO
        return ret

    def get_success_url(self):
        return group_aware_reverse('cosinnus:file:list',
                       kwargs={'group': self.group,
                               'slug': self.object.slug})


class FileIndexView(RequireReadMixin, RedirectView):
    permanent = False

    def get_redirect_url(self, **kwargs):
        return group_aware_reverse('cosinnus:file:list',
                       kwargs={'group': self.group})

file_index_view = FileIndexView.as_view()

class FileHybridListView(RequireReadWriteHybridMixin, HierarchyPathMixin, HierarchicalListCreateViewMixin, 
                             CosinnusFilterMixin, FileFormMixin, AjaxFormsCreateViewMixin, CreateView):
    template_name = 'cosinnus_file/file_list.html'
    filterset_class = FileFilter
    
    model = FileEntry
    form_view = 'create'
    form_class = FileForm
    
    ajax_form_partial = 'cosinnus_file/file_form_core.html'
    ajax_result_partial = 'cosinnus_file/single_file_detailed.html'
    ajax_result_partial_object_alias = 'file'
    
    message_success_folder = _('Folder "%(title)s" was created successfully.')
    
    def get_success_url(self):
        if self.object.is_container:
            messages.success(self.request,
                self.message_success_folder % {'title': self.object.title})
        return group_aware_reverse('cosinnus:file:list', kwargs={
                'group': self.group,
                'slug': self.object.slug})

file_hybrid_list_view = FileHybridListView.as_view()


class FileDeleteView(RequireWriteMixin, FilterGroupMixin, HierarchyDeleteMixin, DeleteView):

    model = FileEntry
    template_name = 'cosinnus_file/file_delete.html'

    def get(self, request, *args, **kwargs):
        try:
            return super(FileDeleteView, self).get(request, *args, **kwargs)
        except Http404:
            messages.error(request, _('File does not exist or you are not allowed to delete it.'))
            return HttpResponseRedirect(self.get_success_url())

    def post(self, request, *args, **kwargs):
        try:
            return super(FileDeleteView, self).post(request, *args, **kwargs)
        except Http404:
            messages.error(request, _('File does not exist or you are not allowed to delete it.'))
            return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        kwargs = {'group': self.group}
        try:
            # if possible, redirect to the object's parent folder list view
            parent_folder = self.object.__class__.objects.get(is_container=True, path=self.object.path)
            kwargs.update({'slug': parent_folder.slug})
        except:
            pass
        return "%s%s" % (group_aware_reverse('cosinnus:file:list', kwargs=kwargs), add_current_params(None, self.request))

file_delete_view = FileDeleteView.as_view()


class FileDetailView(RequireReadMixin, FilterGroupMixin, DetailView):

    model = FileEntry
    template_name = 'cosinnus_file/file_detail.html'

file_detail_view = FileDetailView.as_view()



class FileListView(RequireReadMixin, FilterGroupMixin,
                   FormMixin, HierarchyTreeMixin, ListView):

    form_class = FileListForm
    model = FileEntry
    template_name = 'cosinnus_file/file_list.html'

    def get_context_data(self, **kwargs):
        context = super(FileListView, self).get_context_data(**kwargs)
        tree =  self.get_tree(self.object_list)
        context.update({'filetree': tree})
        return context

    def form_valid(self, form):
        if 'download' in self.request.POST:
            d = form.cleaned_data
            ids = list(map(int, d.get('select', [])))
            files = FileEntry.objects.filter(id__in=ids)
            if not files:
                messages.warning(self.request, _('No files selected.'))
                return HttpResponseRedirect(self.request.path)

            filenames = [(f.file.path, f.file.name) for f in files]
            zf, missing = create_zip_file(filenames)
            download_fn = '_'.join([basename(f.file.name) for f in files])[:50]
            if missing:
                messages.warning(self.request,
                    ungettext(
                        'A problem occurred during export. The following file is missing: %(filename)s.',
                        'A problem occurred during export. The following files are missing: %(filename)s.',
                        len(missing)
                    ) % {
                        'filename': ', '.join(map(basename, missing))
                    }
                )
                return HttpResponseRedirect(self.request.path)
            response = StreamingHttpResponse(open(zf.name, 'rb'), content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename=' + download_fn + '.zip'
            return response

        # Either the request is valid (we offer the download or throw an
        # appropriate message) or the request ist invalid, (e.g. the user
        # didn't press the 'download' button and ca
        messages.error(self.request, _('Invalid request.'))
        return HttpResponseRedirect(self.request.path)

    def post(self, request, *args, **kwargs):
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        files = self.get_queryset()
        form.fields['select'].choices = [(f.id, '') for f in files]

        if form.is_valid():
            return self.form_valid(form)
        else:
            return self.get(request, *args, **kwargs)

file_list_view = FileListView.as_view()


class FileUpdateView(RequireWriteMixin, FileFormMixin, UpdateView):
    form_view = 'edit'
    form_class = FileForm
    model = FileEntry
    template_name = 'cosinnus_file/file_edit.html'
    
    message_success = _('File "%(title)s" was updated successfully.')
    message_error = _('File "%(title)s" could not be updated.')

    def get_context_data(self, **kwargs):
        context = super(FileUpdateView, self).get_context_data(**kwargs)
        tags = FileEntry.objects.tags()
        context.update({
            'tags': tags
        })
        return context

file_update_view = FileUpdateView.as_view()




class FileDownloadView(RequireReadMixin, RecordLastVisitedMixin, FilterGroupMixin, DetailView):
    '''
        Lets the user download a FileEntry file (file is determined by slug),
        while the user never gets to see the server file path.
        Mime type is guessed based on the file.
        
        The /download/ and /save/ urls point to this view, /save/ has force_download == True
    '''
    model = FileEntry
    force_download = False
    # allow file download in groups when files app is deactivated
    ALLOW_VIEW_ACCESS_WHEN_GROUP_APP_DEACTIVATED = True
    
    def dispatch(self, request, *args, **kwargs):
        self.force_download = kwargs.pop('force_download', self.force_download)
        # remove this, it's only for the browser to have a proper preview download name
        kwargs.pop('pretty_filename', None)
        return super(FileDownloadView, self).dispatch(request, *args, **kwargs)
    

    def render_to_response(self, context, **response_kwargs):
        response = HttpResponseNotFound()
        
        fileentry = self.object
        path = fileentry.file and fileentry.file.path
        if path:
            fp = open(path, 'rb')
            response = HttpResponse(fp.read())
            fp.close()
            content_type, encoding = mimetypes.guess_type(fileentry.sourcefilename)
            filename = fileentry.sourcefilename
            if content_type is None:
                content_type = fileentry.mimetype or 'application/octet-stream'
            response['Content-Type'] = content_type
            response['Content-Length'] = fileentry._filesize
            if encoding is not None:
                response['Content-Encoding'] = encoding

                
            if self.force_download or content_type not in settings.COSINNUS_FILE_NON_DOWNLOAD_MIMETYPES:
                # To inspect details for the below code, see http://greenbytes.de/tech/tc2231/
                user_agent = self.request.META.get('HTTP_USER_AGENT', [])
                if u'WebKit' in user_agent:
                    # Safari 3.0 and Chrome 2.0 accepts UTF-8 encoded string directly.
                    filename_header = 'filename=%s' % clean_filename(filename)
                elif u'MSIE' in user_agent:
                    # IE does not support internationalized filename at all.
                    # It can only recognize internationalized URL, so we do the trick via routing rules.
                    filename_header = ''
                else:
                    # For others like Firefox, we follow RFC2231 (encoding extension in HTTP headers).
                    filename_header = 'filename*=UTF-8\'\'%s' % clean_filename(filename)
                response['Content-Disposition'] = 'attachment; ' + filename_header
            
            # manually marking visited from `RecordLastVisitedMixin`
            self.mark_visited()
            
        return response
    
    
file_download_view = FileDownloadView.as_view()


class RocketFileDownloadView(RecordLastVisitedMixin, DetailView):
    '''
        Lets the user download a FileEntry file (file is determined by slug),
        while the user never gets to see the server file path.
        Mime type is guessed based on the file.
        The /download/ and /save/ urls point to this view, /save/ has force_download == True
    '''
    model = FileEntry
    force_download = False

    def dispatch(self, request, *args, **kwargs):
        self.force_download = kwargs.pop('force_download', self.force_download)
        return super(RocketFileDownloadView, self).dispatch(request, *args, **kwargs)

    def render_to_response(self, context, **response_kwargs):
        response = HttpResponseNotFound()

        fileentry = self.object
        path = fileentry.file and fileentry.file.path
        if path:
            fp = open(path, 'rb')
            response = HttpResponse(fp.read())
            fp.close()
            content_type, encoding = mimetypes.guess_type(fileentry.sourcefilename)
            filename = fileentry.sourcefilename
            if content_type is None:
                content_type = fileentry.mimetype or 'application/octet-stream'
            response['Content-Type'] = content_type
            response['Content-Length'] = fileentry._filesize
            if encoding is not None:
                response['Content-Encoding'] = encoding

            # if self.force_download or content_type not in settings.COSINNUS_FILE_NON_DOWNLOAD_MIMETYPES:
            if True:
                # To inspect details for the below code, see http://greenbytes.de/tech/tc2231/
                user_agent = self.request.META.get('HTTP_USER_AGENT', [])
                if u'WebKit' in user_agent:
                    # Safari 3.0 and Chrome 2.0 accepts UTF-8 encoded string directly.
                    filename_header = 'filename=%s' % clean_filename(filename)
                elif u'MSIE' in user_agent:
                    # IE does not support internationalized filename at all.
                    # It can only recognize internationalized URL, so we do the trick via routing rules.
                    filename_header = ''
                else:
                    # For others like Firefox, we follow RFC2231 (encoding extension in HTTP headers).
                    filename_header = 'filename*=UTF-8\'\'%s' % clean_filename(filename)
                response['Content-Disposition'] = 'attachment; ' + filename_header

            # manually marking visited from `RecordLastVisitedMixin`
            self.mark_visited()

        return response


rocket_file_download_view = RocketFileDownloadView.as_view()


class FolderDownloadView(RequireReadMixin, FilterGroupMixin, DetailView):
    '''
        Lets the user download a FileEntry file (file is determined by slug),
        while the user never gets to see the server file path.
        Mime type is guessed based on the file.
        
        The /download/ and /save/ urls point to this view, /save/ has force_download == True
        
        This view also accepts a GET param list `files` with file ids, and will further filter
        the download to only those files in the list. 
        Example: /download/?files=123&files=377
        
    '''
    model = FileEntry
    
    def dispatch(self, request, *args, **kwargs):
        # if we have no object parameter, we're looking at the root folder
        if not 'slug' in kwargs:
            kwargs['slug'] = '_root_'
            self.kwargs = kwargs
        return super(FolderDownloadView, self).dispatch(request, *args, **kwargs)

    def render_to_response(self, context, **response_kwargs):
        
        # check if object is a folder
        folder = self.object
        if not folder.is_container:
            messages.error(self.request, _('Downloading failed, the target object was not a folder!'))
            return HttpResponseRedirect(group_aware_reverse('cosinnus:file:list', kwargs={'group': self.group}))
        
        base_path = folder.path
        files = []
        
        file_filter_ids = [int(fileid) for fileid in self.request.GET.getlist('files')]
        temp_file_paths = []
        # for all files below this folder collect tuples of (filepath on disc, relative file path, )
        for sub_file in FileEntry.objects.filter(group=self.group, path__startswith=base_path, is_container=False):
            # filter for specific files
            if file_filter_ids and not sub_file.id in file_filter_ids:
                continue
            # if only one file is requested, redirect to the single file download view so we don't send a silly 1-file zip
            # appearently, this is really confusing for users, so disable this and always download a folder!
            #if len(file_filter_ids) == 1 and file_filter_ids[0] == sub_file.id:
            #    return redirect(group_aware_reverse('cosinnus:file:save', kwargs={'group': sub_file.group, 'slug': sub_file.slug}))
            # check read access for each file. expensive, but secure
            if not check_object_read_access(sub_file, self.request.user):
                continue
            
            # for urls, write the url to a temp file
            if sub_file.is_url:
                fd, temp_path = tempfile.mkstemp()
                with os.fdopen(fd, 'w') as tmp:
                    tmp.write('[InternetShortcut]\nURL=%s' % sub_file.url)
                temp_file_paths.append(temp_path)
                # attach temp file path
                zip_path = sub_file.path.replace(folder.path, '', 1) + clean_filename(slugify(sub_file.title)) + '.url'
                files.append([temp_path, zip_path])
                continue
            
            # we have a real file, check if it exists and add its path
            if not sub_file.file or not sub_file.file.path:
                continue
            zip_path = sub_file.path.replace(folder.path, '', 1) + sub_file._sourcefilename
            files.append([sub_file.file.path, zip_path])
        
        # if no files were found (all folders empty), show error message
        if not files:
            messages.warning(self.request, _('Canceled the download because there seem to be no files in this folder.'))
            return HttpResponseRedirect(group_aware_reverse('cosinnus:file:list', kwargs={'group': self.group, 'slug': folder.slug}))
        
        # uniquify target zip filenames (we might have the same source file in a folder multiple times)
        for sub_file in files:
            if len([True for nil, zfp in files if zfp == sub_file[1]]) > 1:
                # more than one path like this found, append random string
                sub_file[1] = append_string_to_filename(sub_file[1], get_random_string(7))
        
        # Grab ZIP file from in-memory, make response with correct MIME-type and correct content-disposition
        zip_content = create_zip_from_files(files).getvalue()
        zip_filename = clean_filename(folder.title if folder.slug != '_root_' else self.group.name)
        response = HttpResponse(zip_content)
        response['Content-Type'] = "application/x-zip-compressed"
        response['Content-Disposition'] = 'attachment; filename=%s.zip' % zip_filename
        # fixme: root folder title!
        response['Content-Length'] = len(zip_content)
        
        # clean up temp files
        try:
            for temp_file_path in temp_file_paths:
                os.remove(temp_file_path)
        except:
            pass
        
        return response
    
    
folder_download_view = FolderDownloadView.as_view()


class FileMoveElementView(MoveElementView):
    model = FileEntry

move_element_view = FileMoveElementView.as_view()


class FileDeleteElementView(DeleteElementView):
    model = FileEntry

delete_element_view = FileDeleteElementView.as_view()


def _create_folders_for_path_string(base_folder_object, relative_path_string):
    """ Will create folders for a relative path string, with properly slugified path elements, 
        starting from the base folder object. Will not create any folders if the path exists.
        
        @param base_folder_object: A FileEntry (is_container=True) object
        @param relative_path_string: a path string, eg 'my folder/another sub folder/'. Leading/traling slashes are sanitized.
        @return: The last created sub folder object in the path.  """
        
    relative_path_string = relative_path_string[1:] if relative_path_string.startswith('/') else relative_path_string
    relative_path_string = relative_path_string[:-1] if relative_path_string.endswith('/') else relative_path_string
    
    current_folder = base_folder_object
    for current_path_part in relative_path_string.split('/'):
        slug_part = slugify(current_path_part)
        if not slug_part:
            continue
        next_path = '%s%s/' % (current_folder.path, slug_part) 
        next_folder, created = FileEntry.objects.get_or_create(is_container=True, group=base_folder_object.group, path=next_path, defaults={'title': current_path_part})
        current_folder = next_folder
    
    return current_folder


def file_upload_inline(request, group):
    """ Inline file upload to be called from jQuery FileUpload.
        @param request.on_success: Determines what kind of data will be sent back, and in cosinnus.JS, 
                                    determines what will be done with the data. Options:
            - 'add_to_select2' (default): Will render a select2 pill and in JS, append it to the attach-file select2 field.
            - 'refresh_page' will add a message to the request and in JS refresh the browser page
            - 'render_object' will render the single file template(s) and in JS append them to the file list """
    if not request.is_ajax() or not request.method=='POST':
        return HttpResponseNotAllowed(['POST'])
    
    on_success = request.POST.get('on_success', 'add_to_select2')
    direct_upload = request.POST.get('direct_upload', False)
    make_private = request.POST.get('private_upload', False)
    
    
    # resolve group either from the slug, or like the permission group mixin does ist
    # (group type needs to also be used for that=
    group = get_group_for_request(group, request)
    if not group:
        logger.error('No group found when trying to upload a file!', extra={'group_slug': group, 
            'request': request, 'path': request.path})
        return JSONResponse({'status': 'error', 'message': _('Internal Error: Group not Found')})
    
    # do permission checking using has_write_access(request.user, group)
    if not check_group_create_objects_access(group, request.user):
        logger.error('Permission error while uploading an attached file directly!', 
             extra={'user': request.user, 'request': request, 'path': request.path, 'group_slug': group})
        return JSONResponse({'status': 'error', 'message': _('Permission for upload denied')})
    
    # add any other required kwargs (group) and stuff correctly so the form can be saved
    post = request.POST
    post._mutable = True
    post.update({
        'group_id': group.id
    })
    
    
    base_upload_folder = None
    upload_to_attachment_folder = False
    if 'target_folder' in post:
        base_upload_folder = get_object_or_404(FileEntry, id=int(post.get('target_folder')))
    if not base_upload_folder:
        # check if the group has a folder with slug 'uploads' and if not, create one
        base_upload_folder = get_or_create_attachment_folder(group)
        upload_to_attachment_folder = True
    
    file_info_array = json.loads(post.get('file_info', '[]'))
    result_list = []
    for file_index, dict_file in enumerate(request.FILES.getlist('file')):
        upload_folder = None
        # unless we are uploading as attachment, see if we have any further folder info for this file
        if not upload_to_attachment_folder and len(file_info_array) > file_index:
            # get relative path for the ith file, it should be the same as in the FILES list
            relative_path = file_info_array[file_index]['relative_path']
            name = file_info_array[file_index]['name']
            if relative_path:
                # sanity check, file name in file info must match FILES file name
                if not name == dict_file._name:
                    logger.warn('File upload sanity check failed: File order of file with relative path info and FILES list did not match! (Upload may have sorted the user\'s file in the wrong folder)', extra={
                        'file_info': file_info_array, 'FILES_list': request.FILES.getlist('file')})
                upload_folder = _create_folders_for_path_string(base_upload_folder, relative_path)
                # switch mode to refresh page if we had at least one folder upload
                on_success = 'refresh_page'
                
        if not upload_folder:
            upload_folder = base_upload_folder
            
        single_file_dict = MultiValueDict({'file': [dict_file]})
        post.update({
            'title': clean_single_line_text(dict_file._name),
        })
        form = FileForm(post, single_file_dict, group=group, initial={})
        if form.is_valid():
            # form.instance is the FileEntry, not the media tag
            form.instance.group = group
            form.instance.creator = request.user
            form.instance.path = upload_folder.path
            form.instance._filesize = form.instance.file.file.size
            if not direct_upload:
                form.instance.no_notification = True # disable notifications on non-direct (attached, etc) uploads
            saved_file = form.save()
            
            # flag for uploading the file visible only to oneself, as used in message attachments
            if make_private:
                saved_file.media_tag.visibility = BaseTagObject.VISIBILITY_USER
                saved_file.media_tag.save()
                
            # render either for the file list or for the attached objects
            if on_success == 'render_object':
                context = {
                    'file': saved_file,
                    'do_highlight': True
                }
                result_list.append(render_to_string('cosinnus_file/single_file_detailed.html', context, request))
            else:
                # pipe the file into the select2 JSON representation to be displayed as select2 pill 
                pill_id, pill_html = build_attachment_field_result('cosinnus_file.FileEntry', saved_file)
                result_list.append({'text': pill_html, 'id': pill_id})
        else:
            logger.warn('Form error while uploading an attached file directly!', 
                 extra={'form.errors': form.errors, 'user': request.user, 'request': request, 
                        'path': request.path, 'group_slug': group})
            message = _('The uploaded file was invalid.')
            if form.forms['obj'].errors.get('file', None):
                message = form.forms['obj'].errors.get('file', None)
            return JSONResponse({'status': 'error', 'message': message})
            
    if result_list:
        if on_success == 'refresh_page':
            messages.success(request, ungettext('%(count)d File was added successfully.', '%(count)d Files were added successfully.', len(result_list)) % {'count': len(result_list)})
        
        
        return JSONResponse({'status': 'ok', 'on_success': on_success, 'data': result_list})
    else:
        return JSONResponse({'status': 'error', 'message': _('The file you uploaded was too large or the file type was not permitted to be uploaded!')})

