from __future__ import print_function
import logging

from django.core.management.base import BaseCommand

from cosinnus_exchange.cron import PullData

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):
    """Pulls data from all backends defined in COSINNUS_EXCHANGE_BACKENDS """

    def handle(self, *args, **options):
        p = PullData()
        p.do()
