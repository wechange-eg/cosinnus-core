# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.core.management.base import BaseCommand

from cosinnus.models import CosinnusGroup

logger = logging.getLogger('cosinnus')


class Command(BaseCommand):
    help = (
        'One-Time adds "cosinnus_deck" to all group\'s deactivated_apps field.'
        'This is the same as unchecking cosinnus deck as app for the group in its settings.'
    )

    def handle(self, *args, **options):
        groups = CosinnusGroup.objects.all()
        self.stdout.write()
        text = input(
            f'Now setting cosinnus_deck disabled for {str(groups.count())} groups/projects.\n\n'
            'If you are sure you want this, type "YES" to continue: '
        )
        if not text == 'YES':
            print('Canceled deactivation.')
            exit()
        for group in groups:  # importing all group types on purpose
            if group.deactivated_apps:
                group.deactivated_apps = ','.join(list(set(group.deactivated_apps.split(',') + ['cosinnus_deck'])))
            else:
                group.deactivated_apps = 'cosinnus_deck'
            type(group).objects.filter(pk=group.pk).update(deactivated_apps=group.deactivated_apps)
            group.clear_cache()
        self.stdout.write('Done.')
