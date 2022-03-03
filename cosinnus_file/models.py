# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import hashlib
import os
import shutil
import uuid

from os.path import exists, isfile, join

from django.core.exceptions import ValidationError
from django.urls import reverse
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch.dispatcher import receiver
from django.utils.encoding import force_text
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _, pgettext

from cosinnus.conf import settings
from cosinnus.models import BaseTaggableObjectModel
from cosinnus.models.tagged import LikeableObjectMixin

from cosinnus_file.managers import FileEntryManager
from cosinnus.models.tagged import BaseHierarchicalTaggableObjectModel
from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user
from cosinnus.utils.urls import group_aware_reverse
from cosinnus_file import cosinnus_notifications
from django.contrib.auth import get_user_model
from cosinnus.utils.files import get_cosinnus_media_file_folder
from cosinnus.utils.functions import unique_aware_slugify
from cosinnus.models.mixins.images import ThumbnailableImageMixin
from cosinnus.utils.filters import exclude_special_folders
from uuid import uuid1
from cosinnus_file.utils.strings import clean_filename
from cosinnus.views.mixins.media import VideoEmbedFieldMixin


def get_hashed_filename(instance, filename):
    instance._sourcefilename = filename
    time = now()
    path = join(get_cosinnus_media_file_folder(), 'files', force_text(instance.group_id),
        force_text(time.year), force_text(time.month))
    name = '%s%d%s' % (force_text(uuid.uuid4()), instance.group_id, filename)
    newfilename = hashlib.sha1(name.encode('utf-8')).hexdigest()
    return join(path, newfilename)



class FileEntry(ThumbnailableImageMixin, VideoEmbedFieldMixin, LikeableObjectMixin, BaseHierarchicalTaggableObjectModel):
    """
    Model for uploaded files.

    Files are saved under 'cosinnus_files/groupid/Year/Month/hashedfilename'

    The content type for files is saved in self.mimetype. It finds a special application
    in defining whether a FileEntry is an image (self.is_image).

    Image-files are ~additionally~ copied to '/cosinnus_files/images/hashedfilename.<ext>'
    during the first request of self.static_image_url.
    This then returns that path in the images folder, so the image can be served from a
    publicly suitable location for http requests and so it also shows its file extension.
    The image-copy is deleted when the FileEntry is deleted (post_delete).

    """
    SORT_FIELDS_ALIASES = [('title', 'title'), ('created', 'created'), ('creator', 'creator')]

    note = models.TextField(_('Note'), blank=True, null=True)
    file = models.FileField(_('File'), blank=True, null=True,
                            max_length=250, upload_to=get_hashed_filename)
    
    is_url = models.BooleanField(_('Is URL Link'), default=False,
            help_text='Marks that this file only consists of an URL link. '\
                    'The `file` field may be used to download a preview image.')
    url = models.URLField(_('URL'), blank=True, null=True, max_length=250,
            help_text='For files with `is_url` set to True, this is the URL link. '\
                    'For actual file uploads, this is blank.')
    
    _sourcefilename = models.CharField(blank=False, null=False, default='download', max_length=100)
    _filesize = models.IntegerField(blank=True, null=True, default='0')
    
    mimetype = models.CharField(_('Path'), blank=True, null=True, default='', max_length=50)
    
    objects = FileEntryManager()
    
    image_attr_name = 'file'
    video_url_field_name = 'url'
    
    timeline_template = 'cosinnus_file/v2/dashboard/timeline_item.html'
    
    class Meta(BaseTaggableObjectModel.Meta):
        ordering = ['-created', 'title']
        verbose_name = _('File')
        verbose_name_plural = _('Files')

    def __init__(self, *args, **kwargs):
        super(FileEntry, self).__init__(*args, **kwargs)
        self._meta.get_field('creator').verbose_name = _('Uploaded by')
        self._meta.get_field('created').verbose_name = _('Uploaded on')
        
    @property
    def filesize(self):
        if not self.file or not self._filesize:
            return 0
        return self._filesize
    
    @property
    def is_image(self):
        if not self.file or not self.mimetype:
            return False
        return self.mimetype.startswith('image/') and not self.mimetype == 'image/pdf'
    
    @property
    def wrap_self_attached_images(self):
        """ A wrapper dict that has the file itself as property `attached_images`.
            Useful for reusing attached image templates. """
        return {'attached_images': [self]} if self.is_image else {}
    
    @property
    def sourcefilename(self):
        return self._sourcefilename

    def __str__(self):
        return '%s (%s%s)' % (self.title, self.path, '' if self.is_container else self.sourcefilename)

    def clean(self):
        # if we are creating a file, require an uploaded file (not required for folders)
        # also not required for URL file types
        if not self.is_container and self.file.name is None and not self.url:
            raise ValidationError(_('No files selected.'))

    def save(self, *args, **kwargs):
        if self.path[-1] != '/':
            self.path += '/'
        if len(self.mimetype) > 50:
            self.mimetype = self.mimetype[:50]    
        created = bool(self.pk) == False
        # mark as URL filetype if not file but a URL is given
        if self.url and not self.file:
            self.is_url = True
        super(FileEntry, self).save(*args, **kwargs)
        if created and not self.is_container and not getattr(self, 'no_notification', False):
            # file was created
            session_id = uuid1().int
            group_followers_except_creator_ids = [pk for pk in self.group.get_followed_user_ids() if not pk in [self.creator_id]]
            group_followers_except_creator = get_user_model().objects.filter(id__in=group_followers_except_creator_ids)
            cosinnus_notifications.followed_group_file_created.send(sender=self, user=self.creator, obj=self, audience=group_followers_except_creator, session_id=session_id)
            cosinnus_notifications.file_created.send(sender=self, user=self.creator, obj=self, audience=get_user_model().objects.filter(id__in=self.group.members).exclude(id=self.creator.pk), session_id=session_id, end_session=True)
            
        # sanity check for files that have gotten the image mimetype but aren't readable
        if self.is_image and not self.static_image_url():
            self.mimetype = 'application/octet-stream' # mark as not image
            self.save(update_fields=['mimetype'])

    def get_absolute_url(self):
        if self.is_url:
            return self.url
        if self.is_image:
            kwargs = {'group': self.group}
            if self.container:
                kwargs['slug'] = self.container.slug
            return group_aware_reverse('cosinnus:file:list', kwargs=kwargs) + '?id=%s' % self.id
        kwargs = {
            'group': self.group,
            'slug': self.slug,
            'pretty_filename': clean_filename(self.sourcefilename.replace(' ', '-'))
        }
        return group_aware_reverse('cosinnus:file:pretty-download', kwargs=kwargs)
    
    def get_download_url(self):
        if self.is_url:
            return self.url
        kwargs = {'group': self.group, 'slug': self.slug}
        return group_aware_reverse('cosinnus:file:save', kwargs=kwargs)
    
    def get_delete_url(self):
        kwargs = {'group': self.group,
                  'slug': self.slug}
        return group_aware_reverse('cosinnus:file:delete', kwargs=kwargs)
    
    @classmethod
    def get_current(self, group, user):
        """ Returns a queryset of the current (non-attachment) files """
        qs = FileEntry.objects.filter(group=group)
        qs = exclude_special_folders(qs)
        if user:
            qs = filter_tagged_object_queryset_for_user(qs, user)
        return qs.filter(is_container=False)
    
    def grant_extra_read_permissions(self, user):
        """ Users tagged in files can always see that file, even if it is private. 
            Used for sharing files in direct messages etc. """
        return user in self.media_tag.persons.all()
    
    def get_icon(self):
        """ Returns the font-awesome icon specific to the file type """
        return 'fa-link' if self.is_url else 'fa-file'


def get_or_create_attachment_folder(group):
    attachment_folder = None
    try:
        attachment_folder = FileEntry.objects.get(is_container=True, group=group,
              special_type='attached')
    except FileEntry.DoesNotExist:
        pgettext('special_folder_type', 'Attachments') # leave this for i18n to find!
        attachment_folder = FileEntry(title='Attachments', is_container=True, group=group,
              special_type='attached')
        unique_aware_slugify(attachment_folder, 'title', 'slug')
        attachment_folder.path = '/%s/' % attachment_folder.slug
        attachment_folder.save()
    return attachment_folder


@receiver(post_delete, sender=FileEntry)
def post_file_delete(sender, instance, **kwargs):
    """
    When the user deletes a FileEntry, delete the file on the disk,
    and delete the media-image copy of the file if it was an image.
    """
    if instance.file:
        # delete media image file if it existed
        if instance.is_image:
            imagepath_local = join(settings.MEDIA_ROOT, instance.get_media_image_path())
            if exists(imagepath_local):
                os.remove(imagepath_local)

        path = instance.file.path
        if exists(path) and isfile(path):
            instance.file.delete(False)


import django
if django.VERSION[:2] < (1, 7):
    from cosinnus_file import cosinnus_app
    cosinnus_app.register()
