# -*- coding: utf-8 -*-
from __future__ import unicode_literals

"""
.. warning::

    This file's imports are not guaranteed to be fully backwards functional.
    When Django core changed something that does not offer a simple deprecation
    we may use functions from here.
"""

import warnings

try:
    from django.db.transaction import atomic
except ImportError:
    from django.db.transaction import commit_on_success as atomic  # noqa


from collections import OrderedDict

__all__ = ('atomic', 'OrderedDict', )
