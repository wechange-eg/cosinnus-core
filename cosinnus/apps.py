# -*- coding: utf-8 -*-
from django.apps import AppConfig


class CosinnusAppConfig(AppConfig):

    name = 'cosinnus'
    verbose_name = 'My App'

    def ready(self):
        print ">>>>>>>>>>>>>> cosinnus app received ready()"