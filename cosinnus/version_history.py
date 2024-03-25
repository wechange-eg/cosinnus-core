import pytz
from datetime import datetime
from django.utils.translation import gettext_lazy as _

"""
UPDATES includes release notes for each version shown to the users with:
- datetime: datetime-release-timestamp (the time of authoring this update object)
- title: text for dropdown title (i18n)
- short-text: markdown-text for dropdown label and the details page (i18n)
- full-text: markdown-text for the details page (i18n)
"""

UPDATES = {
    '1.20.1': {
        'datetime': datetime(2024, 3, 25, tzinfo=pytz.utc),
        'title': _('Version 1.20.1 released'),
        'short_text': _('Includes Django update, conference improvements and more.'),
        'full_text': _(
            'The update includes:\n'
            '- Update our backend framework Django to version 4 for security fixes and improvements.\n'
            '- Add support for multi-language welcome-emails, sending the user the welcome email in the users selected language (if the translation feature is enabled).\n'
            '- Make conference application questions translatable (if the translation feature is enabled).\n'
            '- Add subtitle field to (non compact) conferences for additional information.\n'
            '- Show exact number of conference participants for events exceeding 99 participants.\n'
            '- (Admin) Create logs for group and group membership changes.\n'
            '- Remove workshop visibility label and order simultaneous workshops alphabetically on the compact conferences micro site.\n'
            '- Fix map search filter for conferences and events considering ongoing events and exact event ranges.\n'
            '- Fix embedded map page allowing to close selected elements.\n'
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
        'short_text': _('Includes the "What\'s New" feature, a quick way to copy conference invitations, a security update, and more.'),
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
