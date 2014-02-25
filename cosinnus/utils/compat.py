# -*- coding: utf-8 -*-
from __future__ import unicode_literals

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


try:  # pragma: no cover
    from collections import OrderedDict
except ImportError:  # pragma: no cover
    from django.utils.datastructures import SortedDict as OrderedDict  # noqa

__all__ = ('atomic', 'OrderedDict', )
