# most settings are imported from cosinnus.default_settings
from cosinnus.default_settings import *

"""
Basic standalone settings that allow to initialize cosinnus without a portal.
"""

SITE_ID = 1
COSINNUS_PORTAL_URL = "localhost"
COSINNUS_PORTAL_NAME = "dummy"


def define_cosinnus_project_settings(entrypoint_settings):
    # import all cosinnus-core base settings
    project_base_path = environ.Path(__file__) - 3  # type: environ.Path
    vars().update(entrypoint_settings)
    vars().update(define_cosinnus_base_settings(vars(), project_base_path)) # noqa
    return vars()


vars().update(define_cosinnus_project_settings(vars()))


# adjust settings to be able to initialize Django without a portal
ROOT_URLCONF = "cosinnus.tests.settings.standalone_urls"
INSTALLED_APPS.remove('apps.core')
