# -*- coding: utf-8 -*-

from cosinnus.models.group import *  # noqa
from cosinnus.models.profile import *  # noqa
from cosinnus.models.tagged import *  # noqa

from cosinnus.core.loaders.apps import cosinnus_app_registry
cosinnus_app_registry.autodiscover()
