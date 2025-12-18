# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import DEFAULT_DB_ALIAS, connection, connections
from django.db.utils import OperationalError


def get_fields_from_multiform(multiform):
    """Returns all fields from all forms grouped by their form"""
    return multiform._combine('fields')


def get_fieldnames_from_multiform(multiform):
    """Returns all field names for all forms grouped by their form"""
    return {n: list(f.fields.keys()) for n, f in list(multiform.forms.items())}


def table_exists(table_name: str) -> bool:
    """Returns True if a table with the given name exists"""

    return table_name in connection.introspection.table_names()


def is_db_ready(alias: str = DEFAULT_DB_ALIAS) -> bool:
    """Returns True if the database is ready for use"""
    try:
        conn = connections[alias]
        conn.ensure_connection()
        return True
    except OperationalError:
        return False
