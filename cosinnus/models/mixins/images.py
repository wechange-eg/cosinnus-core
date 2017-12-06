# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import os
import shutil
from os.path import exists, join

from django.core.exceptions import ImproperlyConfigured

from cosinnus.conf import settings
from easy_thumbnails.files import get_thumbnailer
from easy_thumbnails.exceptions import InvalidImageFormatError

logger = logging.getLogger('cosinnus')


class ThumbnailableImageMixin(object):
    
    image_attr_name = None # must be defined!
    
    def __init__(self, *args, **kwargs):
        if self.image_attr_name is None:
            raise ImproperlyConfigured('Must set a local attribute ``image_attr_name`` that points to your image field for ThumbnailableImageMixin')
        return super(ThumbnailableImageMixin, self).__init__(*args, **kwargs)
    
    @property
    def is_image(self):
        """ can be override to use with FileFields where it's not sure if it is an image """
        return True
    
    @property
    def sourcefilename(self):
        """ Must alwas return the original image's filename.
            Can be overridden in case the original image was copied away. """
        return self.image.path.split(os.sep)[-1]
    
    def static_image_url(self, size=None, filename_modifier=None):
        """
        This function copies the image to its new path (if necessary) and
        returns the URL for the image to be displayed on the page. (Ex:
        '/media/cosinnus_files/images/dca2b30b1e07ed135c24d7dbd928e37523b474bb.jpg')

        It is a helper function to display cosinnus image files on the webpage.

        The image file is copied to a general image folder in cosinnus_files,
        so the true image path is not shown to the client.

        """
        if not self.is_image:
            return ''
        if not size:
            size = settings.COSINNUS_IMAGE_MAXIMUM_SIZE_SCALE
            
        # the modifier can be used to save images of different sizes
        media_image_path = self.get_media_image_path(filename_modifier=filename_modifier)

        # if image is not in media dir yet, resize and copy it
        imagepath_local = join(settings.MEDIA_ROOT, media_image_path)
        if not exists(imagepath_local):
            thumbnailer = get_thumbnailer(getattr(self, self.image_attr_name))
            try:
                thumbnail = thumbnailer.get_thumbnail({
                    'crop': 'scale',
                    'size': size,
                })
            except InvalidImageFormatError:
                logger.warn('Invalid Image format on an object', extra={'class': self.__class__.__name__, 'id': getattr(self, 'id')})
                return ''
            
            if not thumbnail:
                return ''
            try:
                shutil.copy(thumbnail.path, imagepath_local)
            except IOError:
                # if the file wasn't found, we don't need to crash, people can reupload a broken image
                pass
        
        media_image_path = media_image_path.replace('\\', '/')  # fix for local windows systems
        return join(settings.MEDIA_URL, media_image_path)
    
    
    def static_image_url_thumbnail(self):
        return self.static_image_url(settings.COSINNUS_IMAGE_THUMBNAIL_SIZE_SCALE, 'small')
    
    def get_media_image_path(self, filename_modifier=None):
        """Gets the unique path for each image file in the media directory"""
        mediapath = join('cosinnus_files', 'image_thumbnails')
        mediapath_local = join(settings.MEDIA_ROOT, mediapath)
        if not exists(mediapath_local):
            os.makedirs(mediapath_local)
        filename_modifier = '_' + filename_modifier if filename_modifier else ''
        image_filename = getattr(self, self.image_attr_name).path.split(os.sep)[-1] + filename_modifier + '.' + self.sourcefilename.split('.')[-1]
        return join(mediapath, image_filename)
