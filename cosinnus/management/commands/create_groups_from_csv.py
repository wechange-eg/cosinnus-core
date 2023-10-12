import csv
import logging
import requests
import time

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from cosinnus.core.registries import app_registry
from cosinnus.models.group import CosinnusGroupMembership
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety
from cosinnus.models.membership import MEMBERSHIP_ADMIN
from cosinnus.utils.group import get_cosinnus_group_model


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):
    help = (
        'Imports groups and projects from a CSV file. Expected columns: Type (Gruppe/Projekt), Name, Parent-Group, '
        'Admin-E-Mails (coma-separated), Logo URL, 3rd-Party-Link (optional). To import 3rd-party links, set the tool '
        'name using the third-party-tool-name parameter. Existing groups are skipped.'
    )

    # expected column numbers.
    COL_TYPE = 0
    COL_NAME = 1
    COL_PARENT = 2
    COL_ADMINS = 3
    COL_LOGO = 4
    COL_THIRD_PARTY_LINK = 5

    def add_arguments(self, parser):
        parser.add_argument('csv', type=str, help='CSV file with groups definitions.')
        parser.add_argument('--delimiter', type=str, default=',', help='CSV delimiter (default ",").')

        # parameter for 3rd party tool link
        parser.add_argument(
            '--third-party-tool-name', type=str,
            help=f'If set, importing the links in column 6 as third_party_tools with the given name.'
        )

    def handle(self, *args, **options):
        csv_file_name = options.get('csv')
        delimiter = options.get('delimiter')
        third_party_tool_name = options.get('third_party_tool_name')

        count = 0
        with open(csv_file_name, newline='') as csv_file:
            reader = csv.reader(csv_file, delimiter=delimiter)
            for row in reader:

                # skip empty rows (e.g. empty line at the end of the file)
                if not row:
                    continue

                # check number of columns considering the optional 3rd-party-tool column
                expected_col_num = 6 if third_party_tool_name else 5
                if len(row) < expected_col_num:
                    self.stderr.write(f'Line {reader.line_num}: Invalid number of columns.')
                    return

                # skip header
                if reader.line_num == 1 and row[self.COL_TYPE] not in ['Projekt', 'Gruppe']:
                    self.stdout.write(self.style.WARNING('Skipping header row.'))
                    continue

                # read group type
                group_type = row[self.COL_TYPE]
                if group_type not in ['Projekt', 'Gruppe']:
                    self.stderr.write(f'Line {reader.line_num}: Invalid "Art" value. Expected "Gruppe" or "Projekt".')
                    return
                group_cls = CosinnusSociety if group_type == 'Gruppe' else CosinnusProject

                # read group name
                group_name = row[self.COL_NAME]
                if not group_name:
                    self.stderr.write(f'Line {reader.line_num}: Missing group name.')
                    return

                # Skip existing groups
                if group_cls.objects.filter(name__iexact=group_name).exists():
                    self.stdout.write(self.style.WARNING(f'Skipping existing group "{group_name}".'))
                    continue

                # read parent group
                CosinnusGroup = get_cosinnus_group_model()
                parent_group_name = self._get_optional_value(row[self.COL_PARENT])
                parent_group = None
                if parent_group_name:
                    if not CosinnusGroup.objects.filter(name=parent_group_name).exists():
                        self.stderr.write(f'Line {reader.line_num}: Parent group does not exist.')
                        return
                    parent_group = CosinnusGroup.objects.get(name=parent_group_name)

                # read admins
                User = get_user_model()
                admin_emails_string = row[self.COL_ADMINS]
                if not admin_emails_string:
                    self.stderr.write(f'Line {reader.line_num}: Missing admins.')
                    return
                admin_emails = [name.strip() for name in admin_emails_string.lower().split(',')]
                admins = []
                for admin_email in admin_emails:
                    admin = User.objects.filter(email__iexact=admin_email).first()
                    if not admin:
                        self.stderr.write(f'Line {reader.line_num}: User "{admin_email}" does not exist.')
                        return
                    admins.append(admin)

                # logo
                logo_url = self._get_optional_value(row[self.COL_LOGO])

                # 3rd-party link
                third_party_tool_link = None
                if third_party_tool_name:
                    third_party_tool_link = self._get_optional_value(row[self.COL_THIRD_PARTY_LINK])


                # create group
                group = self._create_group(group_cls, group_name, admins, parent=parent_group)

                # set logo
                if logo_url:
                    self._set_avatar(group, logo_url)

                # set 3rd party link
                if third_party_tool_name and third_party_tool_link:
                    group.third_party_tools = [{'label': third_party_tool_name, 'url': third_party_tool_link}]
                    group.save()

                count += 1

            if count > 0:
                # make sure elastic-search group indexing thread is finished before exiting.
                time.sleep(5)
                self.stdout.write(self.style.SUCCESS(f'{count} groups successfully created.'))
            else:
                self.stdout.write(self.style.WARNING(f'No groups created'))

    def _get_optional_value(self, value):
        """ Read an optional values considering '-' as None. """
        return value if value and value != '-' else None

    def _get_default_deactivated_apps(self):
        """ Returns default deactivated apps for a group. """
        deactivated_apps = []
        for app_name in app_registry:
            if not app_registry.is_active_by_default(app_name) and app_registry.is_deactivatable(app_name):
                deactivated_apps.append(app_name)
        return ','.join(deactivated_apps)

    def _get_default_microsite_public_apps(self):
        """ Returns default microsite apps for a group. """
        microsite_apps = []
        for app_name in app_registry:
            app_disabled = app_name in settings.COSINNUS_GROUP_APPS_WIDGETS_MICROSITE_DISABLED
            if app_registry.is_active_by_default(app_name) and not app_disabled:
                microsite_apps.append(app_name)
        return ','.join(microsite_apps)

    def _create_group(self, group_cls, name, admins, parent=None):
        """ Creates a group and memberships for admins. """
        deactivated_apps = self._get_default_deactivated_apps()
        microsite_public_apps = self._get_default_microsite_public_apps()
        group = group_cls.objects.create(
            name=name, parent=parent, deactivated_apps=deactivated_apps, microsite_public_apps=microsite_public_apps,
        )
        for admin in admins:
            CosinnusGroupMembership.objects.create(group=group, user=admin, status=MEMBERSHIP_ADMIN)
        self.stdout.write(self.style.SUCCESS(f'Created group "{name}".'))
        return group

    def _set_avatar(self, group, avatar_url):
        """ Setting avatar from url. Errors are ignored. """
        try:
            image_ext = avatar_url.split('.')[-1]
            image = ContentFile(requests.get(avatar_url).content)
            group.avatar.save(f'avatar.{image_ext}', image)
        except Exception:
            self.stderr.write(f'Error while setting avatar from logo url {avatar_url}.')
