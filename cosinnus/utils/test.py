# -*- coding: utf-8 -*-
from __future__ import unicode_literals


def get_fields_from_multiform(multiform):
    """Returns all fields from all forms grouped by their form"""
    return multiform._combine('fields')


def get_fieldnames_from_multiform(multiform):
    """Returns all field names for all forms grouped by their form"""
    return {n: list(f.fields.keys()) for n, f in multiform.forms.items()}
