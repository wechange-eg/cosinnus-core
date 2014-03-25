# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import hashlib
import tempfile
import zipfile

from os import path

from cosinnus.conf import settings


def get_avatar_filename(instance, filename):
    _, ext = path.splitext(filename)
    filedir = path.join('cosinnus', 'avatars', 'users')
    name = '%s%d%s' % (settings.SECRET_KEY, instance.user_id, filename)
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
