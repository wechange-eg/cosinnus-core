# ruff: noqa: E501
from datetime import datetime

import pytz
from django.utils.text import format_lazy
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

_REDESIGN_FULL_IS_ENABLED = settings.COSINNUS_V3_FRONTEND_ENABLED and settings.COSINNUS_V3_FRONTEND_EVERYWHERE_ENABLED

UPDATES = {
    '2.6.0': {
        'datetime': datetime(2025, 10, 13, tzinfo=pytz.utc),
        'title': format_lazy(_('Version {version_number} released'), version_number='2.6.0'),
        'short_text': _('This update includes several features and bugfixes:'),
        'full_text': [
            # Deck integration only
            _(
                '- Introducing the task board. You can now enable the modern task board in your groups '
                'and projects, which replaces the todo app. You can migrate your todos from the todos app, '
                'as well as any personal nextcloud boards you might have had.\n'
            )
            if settings.COSINNUS_DECK_ENABLED
            else '',
            # Firebase only
            _('- Added Firebase push integration for push notifications to mobile devices.\n')
            if settings.COSINNUS_FIREBASE_ENABLED
            else '',
            _(
                '- (Admin-Interface) The portal statistics page has been updated and several graphs have been added.\n'
                '- Fixed a bug where the user avatar was sometimes not synced with some integrated services.\n'
                '- Fixed a bug where the platform font face was not applied on some pages.\n'
                '- Fixed a bug where third-party-tool links where sometimes not displayed on the microsite.\n'
                '- Nextcloud groups will now properly be renamed along with their corresponding group/project folder '
                'when their group/project is renamed on the platform.\n'
                '- (BBB) Fixed a bug where existing recorded BBB meetings were not accessible anymore after disabling '
                'BBB meetings for that group/project.\n'
                '- (BBB) Fixed a bug where links to inaccessible BBB meetings would show a server error instead of '
                'an informative error page.\n'
                '- Further minor bugfixes and stability improvements have been made.'
            ),
        ],
    },
    '2.5.0': {
        'datetime': datetime(2025, 7, 16, tzinfo=pytz.utc),
        'title': format_lazy(_('Version {version_number} released'), version_number='2.5.0'),
        'short_text': _('This update includes several bugfixes:'),
        'full_text': [
            _(
                '- Fixed a bug where newly invited group/project members could not join a BBB meeting.\n'
                '- Fixed a bug where admins would see a broken page layout once after logging in.\n'
                '- Fixed a visual bug in the administration interface after clicking a download-link.\n'
                '- Fixed a bug where notifications would not be marked as read when they were too far down in the list.\n'
                '- Added an option to the notification list to mark all notifications as read.\n'
                '- Fixed a bug where event polls could not be created if the user interface was set to certain languages.\n'
                '- Fixed a bug in the legacy messaging system that sometimes prevented writing a new message.\n'
                '- (RocketChat) further improved the stability and performance of the integration with RocketChat.\n'
            ),
            # default password validator settings only
            _(
                '- The password requirements have been changed: Now a password must consist of at least 12 characters. '
                'Otherwise, there are no further requirements regarding the chosen characters. '
                'Passwords are still checked against a list of frequently used passwords.\n'
            )
            if len(settings.AUTH_PASSWORD_VALIDATORS) <= 2
            else '',
            # v3 frontend only
            _(
                '- Fixed a bug that prevented users from completing the intro tour on mobile devices running iOS 18.\n'
                '- Fixed a bug that sometimes prevented entries from being displayed in the '
                'lower part of the sidebar on mobile devices.\n'
            )
            if settings.COSINNUS_V3_FRONTEND_EVERYWHERE_ENABLED
            else '',
        ],
    },
    '2.4.0': {
        'datetime': datetime(2025, 5, 7, tzinfo=pytz.utc),
        'title': _('Version 2.4.0 released'),
        'short_text': _('This update provides several small bugfixes and stability improvements.'),
        'full_text': None,
    },
    '2.3.0': {
        'datetime': datetime(2025, 4, 1, tzinfo=pytz.utc),
        'title': _('Version 2.3.0 released'),
        'short_text': (
            _(
                'This updates provides many visual improvements for the new redesign interface and several small bugfixes and stability improvements.'
            )
            if _REDESIGN_FULL_IS_ENABLED
            else _('This update provides several small bugfixes and stability improvements.')
        ),
        'full_text': None,
    },
    'Redesign': {
        'datetime': datetime(2024, 12, 2, tzinfo=pytz.utc),
        'title': _('Redesign Update'),
        'short_text': _('The redesign has been launched across the platform!'),
        'full_text': _(
            'With the redesign, the user interface has received a major update. This includes a new navigation bar, '
            'a new menu structure in groups and projects, and many small improvements in user interaction.\n\n'
            'This is a stepping stone update for many more exciting features and interface improvements to come '
            'in the near future!'
        ),
        'display_conditional': _REDESIGN_FULL_IS_ENABLED,
    },
    '2.2.5': {
        'datetime': datetime(2024, 12, 1, tzinfo=pytz.utc),
        'title': _('Version 2.2.5 released'),
        'short_text': _('This update includes several bugfixes:'),
        'full_text': _(
            '- Fixed a bug where guest access to BBB meetings was sometimes not possible.\n'
            '- Fixed a bug where users could sometimes not be invited to groups or projects by e-mail.\n'
            '- Fixed a bug where some users could not reset or change their passwords.\n'
            '- Fixed a bug where the text content of markdown editor text boxes was not displayed until the text box was focused.\n'
            '- Fixed a bug where iCal calendar feeds would sometimes not be accessible.\n'
            '- Further minor bugfixes have been made.'
        ),
        'display_conditional': _REDESIGN_FULL_IS_ENABLED,
    },
    '2.2.0': {
        'datetime': datetime(2024, 11, 13, tzinfo=pytz.utc),
        'title': _('Version 2.2.0 released'),
        'short_text': _('This update includes several features and bugfixes:'),
        'full_text': _(
            '- Several improvements have been made to the redesign user interface, and an introductory tooltip tour '
            'has been added.\n'
            '- Further minor bugfixes and stability improvements have been made.'
        ),
        'display_conditional': _REDESIGN_FULL_IS_ENABLED,
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
