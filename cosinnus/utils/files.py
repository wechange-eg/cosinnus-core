# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import tempfile
import zipfile

from os import path


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
