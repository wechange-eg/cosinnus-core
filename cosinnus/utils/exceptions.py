# -*- coding: utf-8 -*-
from __future__ import unicode_literals


class CosinnusPermissionDeniedException(Exception):
    """ Exception to be raised when somewhere deeper than dispatch() in a View it is found that 
        the user needs to be logged in to access it.
        This should always be caught and a proper redirect to a login page should be issued. """
    pass