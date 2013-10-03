# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.forms.widgets import Select

from bootstrap_toolkit.widgets import BootstrapTextInput


class BaseBootstrapInputWidget(BootstrapTextInput):
    append = None
    prepend = None

    def __init__(self, *args, **kwargs):
        self.append = kwargs.get('append', self.append)
        self.prepend = kwargs.get('prepend', self.prepend)
        bootstrap = {
            'append': self.append,
            'prepend': self.prepend,
        }
        kwargs.update(bootstrap)
        super(BaseBootstrapInputWidget, self).__init__(*args, **kwargs)
        self.bootstrap.update(bootstrap)


class BaseBootstrapSelectWidget(Select, BaseBootstrapInputWidget):
    append = None
    prepend = None

    def __init__(self, *args, **kwargs):
        self.append = kwargs.get('append', self.append)
        self.prepend = kwargs.get('prepend', self.prepend)
        super(BaseBootstrapInputWidget, self).__init__(*args, **kwargs)
        self.bootstrap = {
            'append': self.append,
            'prepend': self.prepend,
        }
