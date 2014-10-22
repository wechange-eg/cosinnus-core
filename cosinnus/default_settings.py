# -*- coding: utf-8 -*-
""" Default non-cosinnus specific settings i.e. for third-party apps.
    
    These *MUST* be imported in the settings.py of the app using cosinnus!

    Unless you have a good reason and plan to implement replacement solutions
    you should probably leave these as they are.
    
    For cosinnus-specific internal default settings, check cosinnus/conf.py!
"""

AUTHENTICATION_BACKENDS = ('cosinnus.backends.EmailAuthBackend',)

# select2 render static files
AUTO_RENDER_SELECT2_STATICS = False
    
AWESOME_AVATAR = {
    'width': 120,
    'height': 120,
    'select_area_width': 120,
    'select_area_height': 120,
    'save_quality': 100,
    'save_format': 'png',
    'no_resize': True,
}

FORMAT_MODULE_PATH = 'cosinnus.formats'