# ruff: noqa: E501
from datetime import datetime

import pytz
from django.utils.translation import gettext_lazy as _

from cosinnus.conf import settings

"""
UPDATES includes release notes for each version shown to the users with:
- datetime: datetime-release-timestamp (the time of authoring this update object)
- title: text for dropdown title (i18n)
- short-text: markdown-text for dropdown label and the details page (i18n)
- full-text: markdown-text for the details page (i18n)
- display_conditional: (optional) bool, if this evaluates to False, the update will not be included in the updates list
"""

UPDATES = {
    'Redesign': {
        'datetime': datetime(2024, 10, 15, tzinfo=pytz.utc),
        'title': _('Redesign Update'),
        'short_text': _('The redesign has been launched across the platform!'),
        'full_text': _(
            'With the redesign, the user interface has received a major update. This includes a new navigation bar, '
            'a new menu structure in groups and projects, and many small improvements in user interaction.\n\n'
            'This is a stepping stone update for many more exciting features and interface improvements to come '
            'in the near future!'
        ),
        'display_conditional': (
            settings.COSINNUS_V3_FRONTEND_ENABLED and settings.COSINNUS_V3_FRONTEND_EVERYWHERE_ENABLED
        ),
    },
    '2.1.0': {
        'datetime': datetime(2024, 10, 14, tzinfo=pytz.utc),
        'title': _('Version 2.1.0 released'),
        'short_text': _('This update includes several features and bugfixes:'),
        'full_text': _(
            '- Fixed a bug where registered users could not enter BBB Meetings in public events, projects and groups that they were not a member of.\n'
            '- Fixed a bug where users who wanted to delete their account would incorrectly see an error message saying they were the only admin in a project or group.\n'
            '- Fixed a bug where long text in poll options was sometimes not shown properly.\n'
            '- As an additional account security measure, all user sessions except the current one are now logged out after changing your account password or email.\n'
            '- (RocketChat) improved the stability and performance of the integration with RocketChat (if enabled).\n'
            '- The latest security updates have been applied and further minor bugfixes have been made.\n'
        ),
    },
    '2.0.0': {
        'datetime': datetime(2024, 6, 5, tzinfo=pytz.utc),
        'title': _('Version 2.0.0 released'),
        'short_text': _('This update includes several features and bugfixes:'),
        'full_text': _(
            '- User accounts with unverified email addresses are no longer shown as "inactive" in member lists '
            'and their profiles are now always displayed properly.\n'
            '- Images from external servers that are embedded in user-generated text content \n'
            'will no longer be shown directly in-line, but will be displayed as a link that opens the '
            'image on click. This is done for security reasons and to prevent unwanted trackable \n'
            "connections from the user's browser.\n"
            '- Streamlined some translations in the German user interface to be more gender-neutral.\n'
            '- Fixed a bug where the title of an event was sometimes not readable onevent pages with a dark background image.\n'
            '- Fixed a bug where copying an invitation link in the conference area did not work in some browsers.\n'
            '- Fixed a bug where renaming a project or group was not possible and would fail with an error.\n'
            '- Fixed a bug where the map page did not show a search bar on mobile devices.\n'
            '- Fixed a bug where the map attribution labels were covered by other elements.\n'
            '- Several technical changes have been made under-the-hood to prepare for the redesign.\n'
            '- Some changes and additions have been made to the API for groups and projects.\n'
            '- Further security updates and minor bugfixes have been made.\n'
        ),
    },
    '1.20.4': {
        'datetime': datetime(2024, 5, 6, tzinfo=pytz.utc),
        'title': _('Version 1.20.4 released'),
        'short_text': _('This update includes several bugfixes:'),
        'full_text': _(
            '- Fixed an issue where directly invited users could not enter their initial password.\n'
            '- Fixed an issue where the password reset link would not work in some cases.\n'
            '- Fixed an issue with users were not correctly redirected to the user dashboard after signing up.\n'
            '- Fixed an issue where iCal feeds were sometimes not accessible from external calendar apps.\n'
            '- Fixed an issue where accessing shared pad URLs directly would display an error.\n'
            '- Fixed an issue where guest accounts could not access video conferences (if enabled).\n'
            '- Fixed an issue in the legacy messaging system where the autocomplete function would never finish when entering a recipient.\n'
            '- Fixed an issue where attached images and metadata of todo entries would be removed if completing them from the detail page.\n'
        ),
    },
    '1.20.2': {
        'datetime': datetime(2024, 4, 18, tzinfo=pytz.utc),
        'title': _('Version 1.20.2 released'),
        'short_text': _('This update includes several bugfixes:'),
        'full_text': _(
            '- Fixed an issue with the Markdown text editor in some forms.\n'
            '- Fixed an issue where certain login or signup flows were sometimes not redirecting properly.\n'
        ),
    },
    '1.20.1': {
        'datetime': datetime(2024, 4, 11, tzinfo=pytz.utc),
        'title': _('Version 1.20.1 released'),
        'short_text': _('This update includes several bugfixes:'),
        'full_text': _(
            '- Fixed an issue where users were not correctly redirected after logging in, making it seem like the login had failed.\n'
            '- Further minor bugfixes.\n'
        ),
    },
    '1.20.0': {
        'datetime': datetime(2024, 4, 3, tzinfo=pytz.utc),
        'title': _('Version 1.20.0 released'),
        'short_text': _('Includes Django update, conference improvements and more.'),
        'full_text': _(
            'The update includes:\n'
            '- Updated the backend framework Django to version 4 for security fixes and improvements.\n'
            '- Added support for multi-language welcome-emails, sending the user the welcome email in the users selected language (if the translation feature is enabled).\n'
            '- Made conference application questions translatable (if the translation feature is enabled).\n'
            '- Added subtitle field to conferences for additional information.\n'
            '- Showing exact number of conference participants for events exceeding 99 participants.\n'
            '- Improved map search filter for conferences and events considering ongoing events and exact event ranges.\n'
            '- Improved display of workshops on the compact conferences micro site.\n'
            '- Fixed embedded map page allowing to close selected elements.\n'
            '- (Admin-Interface) Added logs for group and group membership changes.\n'
            '- Further security improvements and minor bugfixes.\n'
        ),
    },
    '1.19.6': {
        'datetime': datetime(2024, 1, 18, tzinfo=pytz.utc),
        'title': _('Version 1.19.6 released'),
        'short_text': _('This update includes several bugfixes:'),
        'full_text': _(
            '- Users whose profile visibility is set to "group/project members only" are now also visible to members of groups/projects they are applying to, instead of being hidden until their membership has been accepted\n'
            '- Fixed a caching issue where accepting a group/project membership request did not immediately make the user a member of that group/project\n'
            '- (OAuth) Changed the login form during OAuth login flows to differentiate from regular logins\n'
            '- (OAuth) Fixed an issue for user account signups when they were initiated from an OAuth flow\n'
            '- (OAuth) Fixed an issue with OAuth logins when the user avatar was too large\n'
            '- (Nextcloud) Removed the group/project dashboard counter for files in the group/project cloud folder as it was often incorrect\n'
        ),
    },
    '1.19.0': {
        'datetime': datetime(2023, 11, 27, tzinfo=pytz.utc),
        'title': _('Version 1.19.0 released'),
        'short_text': _('Includes further settings for conferences, RocketChat integration improvements and more.'),
        'full_text': _(
            'The update includes:\n'
            '- (BigBlueButton) Added a setting to change the conference room welcome message.\n'
            '- (BigBlueButton) Fixed the presentation file setting of conferences not being inherited by their conference rooms.\n'
            '- (RocketChat) The chat element in the group and project dashboards is now only loaded after it has been actively clicked. This optimizes page loading times and saves resources.\n'
            '- (RocketChat) Security and platform-integration improvements.\n'
            '- Events from event polls are created with a default duration of one hour.\n'
            '- (Admin) Fixed an error that could occur when converting projects to groups or vice versa.\n'
            '- Minor bugfixes and text improvements.\n'
        ),
    },
    '1.18.0': {
        'datetime': datetime(2023, 10, 23, tzinfo=pytz.utc),
        'title': _('Version 1.18.0 released'),
        'short_text': _(
            'Includes the "What\'s New" feature, a quick way to copy conference invitations, a security update, and more.'
        ),
        'full_text': _(
            'The update includes:\n'
            '- A "What\'s new" page, showing the release notes for the platform.\n'
            '- Copy a conference invitation to the clipboard from the conference interface.\n'
            '- Some font changes and improvements.\n'
            '- Fix bug in group and project membership handling.\n'
            '- Tags accross the site now link to the search page.\n'
            '- Fix assigning Todos via the user avatar.\n'
            '- Improve reliability of newsletter sending.\n'
            '- Security updates.\n'
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
