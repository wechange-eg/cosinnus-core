# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import hashlib
import tempfile
import zipfile

from os import path

from cosinnus.conf import settings
from uuid import uuid4
from django.utils.encoding import force_text


def get_avatar_filename(instance, filename):
    return _get_avatar_filename(instance, filename, 'user')

def get_group_avatar_filename(instance, filename):
    return _get_avatar_filename(instance, filename, 'group')


def _get_avatar_filename(instance, filename, folder_type):
    _, ext = path.splitext(filename)
    filedir = path.join('cosinnus', 'avatars', folder_type)
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
