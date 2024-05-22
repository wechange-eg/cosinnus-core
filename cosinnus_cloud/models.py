# -*- coding: utf-8 -*-

from dataclasses import dataclass

import six
from annoying.functions import get_object_or_None
from django.db import models
from django.utils.translation import gettext_lazy as _

from cosinnus.conf import settings
from cosinnus.models.tagged import BaseTaggableObjectModel
from cosinnus_cloud.utils.cosinnus import is_cloud_enabled_for_group


class CloudFile(object):
    """A wrapper object for API-retrieved nextcloud file infos"""

    # uses the internal id to redirect https://<cloud-root>/f/1085
    title = None  # str
    url = None
    download_url = None
    type = None  # ???
    folder = None
    root_folder = None
    path = None
    icon = 'fa-cloud'

    def __init__(
        self, title=None, url=None, download_url=None, type=None, folder=None, root_folder=None, path=None, user=None
    ):
        """Supply a `user` to make download links work for users!"""
        self.title = title
        self.url = url
        self.type = type
        self.folder = folder
        self.root_folder = root_folder
        self.path = path
        if user:
            from cosinnus_cloud.hooks import get_nc_user_id

            self.download_url = download_url.replace(
                settings.COSINNUS_CLOUD_NEXTCLOUD_ADMIN_USERNAME, get_nc_user_id(user), 1
            )
        else:
            self.download_url = download_url

    def get_icon(self):
        return self.icon


@dataclass
class SimpleCloudFile:
    """Similar to CloudFile, but doesn't provide download links, only id and name"""

    id: str  # an int from NC, but prepended for use in the attached object view
    filename: str
    dirname: str

    @property
    def title(self):
        """Proxy for `build_attachment_field_result()`"""
        return self.filename


def _encode_id_data_str(nextcloud_file_id, filename, path):
    """Decodes an id_data_str.
    Pattern: (id:int)_(filename:ordlistwithdash)_(path:ordlistwithdash)"""
    filename_enc = '-'.join([str(ord(char)) for char in filename])
    path_enc = '-'.join([str(ord(char)) for char in path])
    return f'{nextcloud_file_id}_{filename_enc}_{path_enc}'


def _decode_id_data_str(id_data_str):
    """Encodes an `id_data_str`.
    Pattern: (id:int)_(filename:ordlistwithdash)_(path:ordlistwithdash)"""
    try:
        nextcloud_file_id, filename_enc, path_enc = id_data_str.split('_')
        filename = ''.join([chr(int(charcode)) for charcode in filename_enc.split('-')])
        path = ''.join([chr(int(charcode)) for charcode in path_enc.split('-')])
        return (int(nextcloud_file_id), filename, path)
    except Exception:
        if settings.DEBUG:
            raise
        return None


@six.python_2_unicode_compatible
class LinkedCloudFile(BaseTaggableObjectModel):
    nextcloud_file_id = models.IntegerField('Nextcloud File ID', unique=True, blank=False, null=False)
    path = models.CharField(_('Path'), blank=True, null=True, max_length=255)
    url = models.URLField(_('URL'), blank=True, null=True)

    class Meta(BaseTaggableObjectModel.Meta):
        verbose_name = _('Linked Cloud File')
        verbose_name_plural = _('Linked Cloud Files')

    @classmethod
    def get_for_nextcloud_file_id_data_str(cls, id_data_str, group):
        """Creates or retrieves a LinkedCloudFile for the given nextcloud file id.
        If the file link existed already, the data is re-synced."""
        nextcloud_file_id = id_data_str.split('_', 1)[0]
        existing_linked_file = get_object_or_None(cls, nextcloud_file_id=nextcloud_file_id)
        linked_file = existing_linked_file or LinkedCloudFile(nextcloud_file_id=nextcloud_file_id, group=group)
        # populate or if existed, refresh from NC
        try:
            linked_file = linked_file.sync_from_nextcloud_id_data_str(id_data_str)
        except Exception:
            # if there was an error retrieving the NC info, we return the existing linked file or nothing
            if settings.DEBUG:
                raise
            return existing_linked_file or None
        return linked_file

    def sync_from_nextcloud_id_data_str(self, id_data_str):
        """So we don't have to run multiple nextcloud API queries for attached files, we encode the
        data found on the autocomplete search query as `id_data_str` and pass it through the form on POST."""
        data_tuple = _decode_id_data_str(id_data_str)
        if data_tuple is None:
            return None
        nextcloud_file_id, filename, path = data_tuple
        # don't save again if all properties are the same
        if self.nextcloud_file_id == nextcloud_file_id and self.title == filename and self.path == path:
            return self

        self.nextcloud_file_id = nextcloud_file_id
        self.title = filename
        self.path = path
        from cosinnus_cloud.utils import nextcloud

        self.url = nextcloud.get_permalink_for_file_id(nextcloud_file_id)
        self.save()
        return self

    def __str__(self):
        return f'LinkedCloudFile (nc-id: {self.nextcloud_file_id})'

    def get_icon(self):
        """Returns the font-awesome icon specific to this object type"""
        return 'fa-cloud'

    def save(self, *args, **kwargs):
        return super(LinkedCloudFile, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return self.url

    def to_cloud_file(self, request=None):
        """Converts this to a CloudFile, that is used in templates"""
        return CloudFile(
            title=self.title,
            url=self.url,
            download_url=f'{settings.COSINNUS_CLOUD_NEXTCLOUD_URL}/remote.php/webdav{self.path}',
            type=None,
            folder=self.path,
            root_folder=self.path.split('/')[1],
            path=self.path,
            user=request.user if request and request.user and request.user.is_authenticated else None,
        )

    @classmethod
    def get_attachable_objects_query_results(cls, group, request, term, page=1):
        """A droping for `cosinnus.view.attached_object.AttachableObjectSelect2View` to get attachable
        objects in a non-DB-based query."""
        # Check if cloud is enabled for group
        if (
            not is_cloud_enabled_for_group(group)
            or not group.nextcloud_group_id
            or not group.nextcloud_groupfolder_name
        ):
            return []
        from cosinnus_cloud.hooks import get_nc_user_id
        from cosinnus_cloud.utils import nextcloud

        simple_cloud_files = nextcloud.get_groupfiles_match_list(
            userid=get_nc_user_id(request.user),
            folder=group.nextcloud_groupfolder_name,
            name_query=term,
            page=page,
            page_size=10,
        )
        # add a prefix to the ID to signify that the ID doesn't belong to the actual model,
        # but needs to be resolved
        for simple_cloud_file in simple_cloud_files:
            id_data_str = _encode_id_data_str(
                simple_cloud_file.id, simple_cloud_file.filename, simple_cloud_file.dirname
            )
            simple_cloud_file.id = f'_unresolved_{id_data_str}'
        return simple_cloud_files

    @classmethod
    def resolve_attachable_object_id(cls, object_id, group):
        """For _unresolved_ IDs of an attachable object, get an attachable object
        that belongs to that ID (usually an external object's ID is given, and
        we return the local DB object that is attachable and is pointing to it)"""
        return cls.get_for_nextcloud_file_id_data_str(object_id, group)
