# -*- coding: utf-8 -*-

"""
This file contains static i18n strings that are used somewhere in cosinnus, but
for various reasons cannot be picked up by the makemessages parser.
They are included here to be seen by the parser anyways (this file is loaded from __init__.py).
"""

from django.utils.translation import ugettext_lazy as _


_('My Dashboard')
_('Wrong file format. Try .jpg, .jpeg, .png, or .gif instead.')


# use the following pattern to have the strings be included as JS translations:

## Translators: __INCLUDE_JS_PO__
#_('A JS string')