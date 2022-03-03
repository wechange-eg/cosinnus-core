import logging

from django.core.management.base import BaseCommand

from cosinnus.views.housekeeping import ensure_group_widgets


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):
    """
    Runs ensure_group_widgets, generating any group DashboardWidget WidgetConfig objects
    for missing widgets
    """

    def handle(self, *args, **options):
        ret = ensure_group_widgets()
        self.stdout.write(ret)