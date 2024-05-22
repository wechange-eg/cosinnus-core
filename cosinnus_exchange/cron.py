import logging
from importlib import import_module

from django.utils.encoding import force_str
from django_cron import Schedule

from cosinnus.conf import settings
from cosinnus.cron import CosinnusCronJobBase
from cosinnus_exchange.backends import ExchangeBackend

logger = logging.getLogger(__name__)


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

            # we run this import non-threaded on elastisearch to not overload the service
            orig_setting = getattr(settings, 'COSINNUS_ELASTIC_BACKEND_RUN_THREADED', True)
            try:
                setattr(settings, 'COSINNUS_ELASTIC_BACKEND_RUN_THREADED', False)
                backend.pull()
            except Exception as e:
                logger.error(
                    'An error occured during pulling data from an exchange backend! Exception in extra.',
                    extra={'backend': str(backend), 'exc_str': force_str(e), 'exception': e},
                )
                if settings.DEBUG:
                    raise
            finally:
                setattr(settings, 'COSINNUS_ELASTIC_BACKEND_RUN_THREADED', orig_setting)
