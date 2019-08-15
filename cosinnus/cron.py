# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from cosinnus.gooddb import GoodDBConnection
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


class PushToGoodDB(CosinnusCronJobBase):
    """
    Pushes public data from e. g. events and initiatives to GoodDB microservice
    """

    RUN_EVERY_MINS = 1
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)

    cosinnus_code = 'cosinnus.gooddb_push'

    def do(self):
        gdb_connection = GoodDBConnection()
        gdb_connection.push()


class PullFromGoodDB(CosinnusCronJobBase):
    """
    Pulls public data from e. g. events and initiatives to GoodDB microservice
    """

    RUN_EVERY_MINS = 1
    schedule = Schedule(run_every_mins=RUN_EVERY_MINS)

    cosinnus_code = 'cosinnus.gooddb_pull'

    def do(self):
        gdb_connection = GoodDBConnection()
        gdb_connection.pull()
