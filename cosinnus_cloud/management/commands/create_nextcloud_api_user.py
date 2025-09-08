# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from cosinnus.utils.permissions import IsNextCloudApiUser

logger = logging.getLogger('cosinnus')


class Command(BaseCommand):
    help = 'Creates an NextCloud API user and group (e.g. userd in the deck events API).'

    def add_arguments(self, parser):
        parser.add_argument('username', type=str)
        parser.add_argument('password', type=str)

    def handle(self, *args, **options):
        # get username and password
        username = options['username']
        password = options['password']

        # create a fake email
        email = f'{username}@wechange.de'

        # get or create permission group
        group_name = IsNextCloudApiUser.GROUP_NAME
        group = Group.objects.filter(name=group_name).first()
        if group:
            self.stdout.write(self.style.WARNING(f'Group {group_name} already exists.'))
        else:
            group = Group.objects.create(name=group_name)
            self.stdout.write(f'Group {group_name} created.')

        # get or create user
        user = get_user_model().objects.filter(username=username).first()
        if user:
            self.stdout.write(self.style.WARNING(f'User {username} already exists.'))
        else:
            user = get_user_model().objects.create_user(username=username, password=password, email=email)
            self.stdout.write(f'User {username} created.')

        if user.groups.filter(name=group_name).exists():
            self.stdout.write(self.style.WARNING(f'User {username} already in group {group_name}.'))
        else:
            user.groups.add(group)
            self.stdout.write(f'Added user {username} to group {group_name}.')
