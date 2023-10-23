import pytz
from datetime import datetime
from django.utils.translation import ugettext_lazy as _

"""
UPDATES includes release notes for each version shown to the users with:
- datetime: datetime-release-timestamp (the time of authoring this update object)
- title: text for dropdown title (i18n)
- short-text: markdown-text for dropdown label and the details page (i18n)
- full-text: markdown-text for the details page (i18n)
"""

UPDATES = {
    '1.18.0': {
        'datetime': datetime(2023, 10, 23, tzinfo=pytz.utc),
        'title': _('Version 1.18.0 released'),
        'short_text': _('Includes the "What\'s New" feature, conference invitation for the clipboard a security update and more.'),
        'full_text': _(
            'The update includes:\n'
            '- "What\'s new" showing the release notes for the platform.\n'
            '- Copy a conference invitation to clipboard from the conference interface.\n'
            '- Switch font of portals using the "Brandon Text" font to "IBM Plex".\n'
            '- Fix bug in group and project membership handling.\n'
            '- Tags of news posts link to a search for the tag.\n'
            '- Fix assigning Todos via the user avatar.\n'
            '- Improve reliability of newsletter sending.\n'
            '- Security update fixing CVE-2023-4863.\n'
            '- Further minor bugfixes.\n'
        ),
    },
    '1.17.1': {
        'datetime': datetime(2023, 9, 13, tzinfo=pytz.utc),
        'title': _('Version 1.17.1 released'),
        'short_text': _('Includes dynamic registration form and dynamic options for participation for conferences.'),
        'full_text': _(
            'The update includes:\n'
            '- Dynamic registration form for conferences\n'
            '- Dynamize options for participation for conferences\n'
            '- Library Update of Moment.js\n'
            '- Update Matomo tracking to include better options\n'
        ),
    },
}
