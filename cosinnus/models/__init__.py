# -*- coding: utf-8 -*-

from cosinnus.models.group import *  # noqa
from cosinnus.models.profile import *  # noqa
from cosinnus.models.tagged import *  # noqa
from cosinnus.models.widget import *  # noqa

from cosinnus.core.loaders import apps, attached_objects, widgets

apps.cosinnus_app_registry.autodiscover()
attached_objects.cosinnus_attached_object_registry.autodiscover()
widgets.cosinnus_widget_registry.autodiscover()
