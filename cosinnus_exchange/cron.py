from importlib import import_module
from django_cron import Schedule

from cosinnus.conf import settings
from cosinnus.cron import CosinnusCronJobBase
from cosinnus_exchange.backends import ExchangeBackend


class PullData(CosinnusCronJobBase):
    """
    Pull data from exchange backends
    """
    if settings.COSINNUS_EXCHANGE_ENABLED:
        RUN_EVERY_MINS = settings.COSINNUS_EXCHANGE_RUN_EVERY_MINS
        schedule = Schedule(run_every_mins=RUN_EVERY_MINS)
    else:
        schedule = Schedule()

    cosinnus_code = 'cosinnus_exchange.pull_data'

    def do(self):
        for conf in settings.COSINNUS_EXCHANGE_BACKENDS:
            backend_params = conf.copy()
            if 'backend' in backend_params:
                backend_module_name, backend_name = backend_params.pop('backend').rsplit('.', 1)
                backend_module = import_module(backend_module_name)
                backend_model = getattr(backend_module, backend_name)
            else:
                backend_model = ExchangeBackend
            backend = backend_model(**backend_params)
            backend.pull()
