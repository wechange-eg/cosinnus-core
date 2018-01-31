# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django_cron import CronJobBase, Schedule

from cosinnus.models.group import CosinnusPortal
from cosinnus.core.middleware.cosinnus_middleware import initialize_cosinnus_after_startup
from django.core.exceptions import ImproperlyConfigured


class CosinnusCronJobBase(CronJobBase):
    
    cosinnus_code = None
        
    @property
    def code(self):
        """ Unique cron id, must contain CosinnusPortal slug, or different portal crons will overlap """
        if not self.cosinnus_code:
            raise ImproperlyConfigured('Must define a ``cosinnus_code`` property for your cron object!')
        return 'p_%s_%s' % (CosinnusPortal.get_current().slug, self.cosinnus_code)
    
    def __init__(self, *args, **kwargs):
        super(CosinnusCronJobBase, self).__init__(*args, **kwargs)
        initialize_cosinnus_after_startup()
    
    def do(self):
        raise ImproperlyConfigured('``do()`` must be overridden in your cron object!')
    