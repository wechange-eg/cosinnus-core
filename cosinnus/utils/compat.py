# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from collections import OrderedDict

"""
.. warning::

    This file's imports are not guaranteed to be fully backwards functional.
    When Django core changed something that does not offer a simple deprecation
    we may use functions from here.
"""

try:
    from django.db.transaction import atomic
except ImportError:
    from django.db.transaction import commit_on_success as atomic  # noqa


__all__ = (
    'atomic',
    'OrderedDict',
)
