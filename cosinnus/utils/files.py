# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import hashlib
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

def get_cosinnus_media_file_folder():
    """ Returns the prefix-folder path for this portal, 
        under which all media and files should be saved. """
    portal_folder = ''.join([ch if ch.isalnum() else '_' for ch in CosinnusPortal().get_current().slug])
    return  path.join('cosinnus_portals', 'portal_%s' % portal_folder)

def get_avatar_filename(instance, filename):
    return _get_avatar_filename(instance, filename, 'user')

def get_group_avatar_filename(instance, filename):
    return _get_avatar_filename(instance, filename, 'group')


def _get_avatar_filename(instance, filename, folder_type):
    _, ext = path.splitext(filename)
    filedir = path.join(get_cosinnus_media_file_folder(), 'avatars', folder_type)
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
