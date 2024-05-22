# encoding: utf-8

from haystack.management.commands.update_index import Command as UpdateIndexCommand

from cosinnus.conf import settings


class Command(UpdateIndexCommand):
    """Proxy for the haystack command `update_index` that disables the
    cosinnus-specific threading for haystack/elasticsearch index updates,
    as updating the index threaded leads to a DB overload."""

    def handle(self, **options):
        # set our threading setting to False
        setattr(settings, 'COSINNUS_ELASTIC_BACKEND_RUN_THREADED', False)
        super().handle(**options)
