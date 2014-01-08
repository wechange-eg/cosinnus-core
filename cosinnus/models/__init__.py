# -*- coding: utf-8 -*-

from cosinnus.models.group import *  # noqa
from cosinnus.models.profile import *  # noqa
from cosinnus.models.tagged import *  # noqa
from cosinnus.models.widget import *  # noqa

from cosinnus.core.loaders.apps import cosinnus_app_registry
cosinnus_app_registry.autodiscover()

# TODO: Move this somewhere it doesn't get loaded on server start
from cosinnus.core.loaders.attached_objects import cosinnus_attached_object_registry
cosinnus_attached_object_registry.autodiscover()
