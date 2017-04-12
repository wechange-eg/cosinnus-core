# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import hashlib
import os
import StringIO
import tempfile
import zipfile

from os import path

from cosinnus.conf import settings
from uuid import uuid4
from django.utils.encoding import force_text
from django.db.models.loading import get_model

# delegate import to avoid cyclic dependencies
_CosinnusPortal = None

def CosinnusPortal():
    global _CosinnusPortal
    if _CosinnusPortal is None: 
        _CosinnusPortal = get_model('cosinnus', 'CosinnusPortal')
    return _CosinnusPortal

def get_cosinnus_all_portals_folder():
    return path.join('cosinnus_portals', 'all_portals')

def get_cosinnus_media_file_folder():
    """ Returns the prefix-folder path for this portal, 
        under which all media and files should be saved. """
    CosinnusPortalClass = CosinnusPortal()
    if CosinnusPortalClass:
        portal_folder = ''.join([ch if ch.isalnum() else '_' for ch in CosinnusPortal().get_current().slug])
        return path.join('cosinnus_portals', 'portal_%s' % portal_folder)
    else:
        return get_cosinnus_all_portals_folder()

def get_avatar_filename(instance, filename):
    return _get_avatar_filename(instance, filename, 'user')

def get_group_avatar_filename(instance, filename):
    return _get_avatar_filename(instance, filename, 'group')

def get_group_gallery_image_filename(instance, filename):
    return _get_avatar_filename(instance, filename, 'gallery_images', base_folder='group_images')

def get_group_wallpaper_filename(instance, filename):
    return _get_avatar_filename(instance, filename, 'group_wallpapers', base_folder='group_images')

def _get_avatar_filename(instance, filename, folder_type, base_folder='avatars'):
    _, ext = path.splitext(filename)
    filedir = path.join(get_cosinnus_media_file_folder(), base_folder, folder_type)
    my_uuid = force_text(uuid4())
    name = '%s%s%s' % (settings.SECRET_KEY, my_uuid , filename)
    newfilename = hashlib.sha1(name.encode('utf-8')).hexdigest() + ext
    return path.join(filedir, newfilename)

def get_portal_background_image_filename(instance, filename):
    return _get_all_portals_filename(instance, filename, 'portal_background_images')

def _get_all_portals_filename(instance, filename, sub_folder='images'):
    _, ext = path.splitext(filename)
    filedir = path.join(get_cosinnus_all_portals_folder(), sub_folder)
    my_uuid = force_text(uuid4())
    name = '%s%s%s' % (settings.SECRET_KEY, my_uuid , filename)
    newfilename = hashlib.sha1(name.encode('utf-8')).hexdigest() + ext
    return path.join(filedir, newfilename)

def create_zip_file(files):
    missing = []
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        with zipfile.ZipFile(tf, 'w', zipfile.ZIP_DEFLATED) as zf:
            for f in files:
                if path.exists(f[0]):
                    zf.write(*f)
                else:
                    missing.append(f[1])
    return tf, missing


def create_zip_from_files(file_list):
    """ Will create an in-memory (StringIO) Zip-File from files on the disk. 
        @param file_list: A list of string tuples: [(local_file_path, relative_zip_path)]
            Example: [('/tmp/file1.txt', 'file1.txt'), ('/tmp/sub/file2.txt', 'sub/file2.txt')]
        @return: A StringIO instance containing the zip in memory """
        
    # Open StringIO to grab in-memory ZIP contents
    stringio = StringIO.StringIO()
    # The zip compressor
    zip_file = zipfile.ZipFile(stringio, "w", zipfile.ZIP_DEFLATED)
    # add files to zip with custom path
    for file_path, zip_path in file_list:
        if path.exists(file_path):
            zip_file.write(file_path, zip_path)
    # Must close zip for all contents to be written
    zip_file.close()
    
    return stringio

def append_string_to_filename(file_path, string_to_append):
    """ Appends a string to *the base file name*, before the file extension, of a given file with path """
    dir_name, file_name = os.path.split(file_path)
    file_root, file_ext = os.path.splitext(file_name)
    return os.path.join(dir_name, "%s_%s%s" % (file_root, string_to_append, file_ext))
                
