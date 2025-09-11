# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
import random

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from cosinnus.models.tagged import BaseTagObject
from cosinnus.utils.permissions import IsNextCloudApiUser

logger = logging.getLogger('cosinnus')


class Command(BaseCommand):
    help = 'Creates an NextCloud API user and group (e.g. used in the deck events API).'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str)
        parser.add_argument('password', type=str)

    def handle(self, *args, **options):
        # get email and password
        email = options['email']
        password = options['password']

        # create a fake username

        # get or create permission group
        group_name = IsNextCloudApiUser.GROUP_NAME
        group = Group.objects.filter(name=group_name).first()
        if group:
            self.stdout.write(self.style.WARNING(f'Group {group_name} already exists.'))
        else:
            group = Group.objects.create(name=group_name)
            self.stdout.write(f'Group {group_name} created.')

        # get or create user
        user = get_user_model().objects.filter(email=email).first()
        if user:
            self.stdout.write(self.style.WARNING(f'User "{email}" already exists.'))
        else:
            username = str(random.randint(100000000000, 999999999999))
            user = get_user_model().objects.create_user(
                username=username, password=password, email=email, first_name='NextCloudApiUser', last_name=''
            )

            # set user id
            user.username = str(user.id)
            user.save()

            # set user visibility to least visisble
            media_tag = user.cosinnus_profile.media_tag
            media_tag.visibility = BaseTagObject.VISIBILITY_USER
            media_tag.save()

            self.stdout.write(f'User {email} created.')

        if user.groups.filter(name=group_name).exists():
            self.stdout.write(self.style.WARNING(f'User {email} already in group {group_name}.'))
        else:
            user.groups.add(group)
            self.stdout.write(f'Added user {email} to group {group_name}.')
