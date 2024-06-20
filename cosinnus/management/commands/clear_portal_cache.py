# encoding: utf-8

from haystack.management.commands.rebuild_index import Command as RebuildIndexCommand

from cosinnus.models.group import CosinnusPortal


class Command(RebuildIndexCommand):
    """A safe cache clear that clears the CosinnusPortal cache entries.
    May be called any time without risk to stability, and is not too expensive."""

    def handle(self, **options):
        CosinnusPortal.get_current().clear_cache()
