# encoding: utf-8

from pathlib import Path

from django.core.management.base import BaseCommand

from cosinnus.views.housekeeping import newsletter_users


class Command(BaseCommand):
    """Writes out the  XLSX file to the home dir containing all users' emails that have signed up for the newsletter,
    usually obtained from the simple statistics /housekeeping/newsletterusers/.
    Can be used if the download/generation takes too long via web, or to circumvent
    COSINNUS_ENABLE_ADMIN_EMAIL_CSV_DOWNLOADS being disabled."""

    def handle(self, **options):
        path = Path.home() / 'newsletter-users-generated.xlsx'
        self.stdout.write(f'Generating newsletter file, will write it to to {path} ...')
        response = newsletter_users(None, override_conf_setting=True)

        with open(path, 'wb') as file:
            file.write(response.content)
        self.stdout.write(f'Done. File written to {path}')
