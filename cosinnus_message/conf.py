# -*- coding: utf-8 -*-
# ruff: noqa :E501
from __future__ import unicode_literals

from builtins import object

from appconf import AppConf
from django.conf import settings  # noqa
from django.utils.translation import gettext_lazy as _


class CosinnusMessageConf(AppConf):
    pass


class CosinnusMessageDefaultSettings(AppConf):
    """Settings without a prefix namespace to provide default setting values for other apps.
    These are settings used by default in cosinnus apps, such as avatar dimensions, etc.
    """

    class Meta(object):
        prefix = ''

    POSTMAN_DISALLOW_ANONYMOUS = True  # No anonymous messaging
    POSTMAN_AUTO_MODERATE_AS = True  # Auto accept all messages
    POSTMAN_SHOW_USER_AS = 'username'

    # Chat config
    COSINNUS_ROCKET_ENABLED = False
    COSINNUS_ROCKET_EXPORT_ENABLED = False

    # the URL for the rocketchat service
    COSINNUS_CHAT_BASE_URL = None

    # the request timeout for rocketchat connections for important system connections
    COSINNUS_CHAT_CONNECTION_TIMEOUT = 30

    # the request timeout for rocketchat user connections, like retrieving unread message counts.
    # should not be too high, as these connections aren't as important and
    # as some requests using user connections are blocking requests, they could clog up
    # the platform's connections if the rocket service is slow
    COSINNUS_CHAT_USER_CONNECTION_TIMEOUT = 5

    # timeout to retry accessing rocketchat after a connection error occurred
    COSINNUS_CHAT_CONSIDER_DOWN_TIMEOUT = 60 * 5  # 5 minutes

    # the keys for the CosinnusGroup.setting object to save the room's id in.
    # will be prefixed as such: "{cosinnus.models.profile.PROFILE_SETTING_ROCKET_CHAT_ID}_{room_key}"
    # Do not change this setting value for portals unless you know exactly what youre doing!
    COSINNUS_ROCKET_GROUP_ROOM_KEYS = [
        'general',
    ]
    # the display name pattern for the channel for the group rooms that will be created
    # will be given the group.slug as format-argument
    COSINNUS_ROCKET_GROUP_ROOM_NAMES_MAP = {
        COSINNUS_ROCKET_GROUP_ROOM_KEYS[0]: '%s',
    }
    # the room where note posts will be posted to by the rocket box
    # set to None to disable note post relaying to rocketchat!
    COSINNUS_ROCKET_NOTE_POST_RELAY_ROOM_KEY = COSINNUS_ROCKET_GROUP_ROOM_KEYS[0]

    # how many words the relayed note may be max. if None, disabled.
    COSINNUS_ROCKET_NOTE_POST_RELAY_TRUNCATE_WORD_COUNT = 60

    # the introductory emote for news post relays by the bot
    COSINNUS_ROCKET_NEWS_BOT_EMOTE = ':loud_sound:'
    # the introductory emote for event post relays by the bot
    COSINNUS_ROCKET_NEWS_BOT_EMOTE_EVENT = ':date:'
    # the introductory explanation message for the users in a "Contact Group" room
    COSINNUS_ROCKET_GROUP_CONTACT_ROOM_INFO_MESSAGE = _(
        'Please post your request or question here. You can see the channel members by clicking the group icon at the top of the channel.'
    )

    # whether to show a "Click here to show chat" message over the rocketchat group dashboard widget
    COSINNUS_ROCKET_GROUP_WIDGET_SHOW_ROADBLOCK = True

    # whether all rocketchat links should open with target="_blank"
    COSINNUS_ROCKET_OPEN_IN_NEW_TAB = False

    COSINNUS_CHAT_SETTINGS = {
        # General
        'UTF8_User_Names_Validation': '[0-9a-zA-Z-_.äÄöÖüÜß]+',
        'UTF8_Channel_Names_Validation': '[0-9a-zA-Z-_.äÄöÖüÜß]+',
        'Favorite_Rooms': True,
        'Iframe_Restrict_Access': False,
        # Accounts
        # 'Accounts_AllowAnonymousRead': False,
        # 'Accounts_AllowAnonymousWrite': False,
        # 'Accounts_AllowDeleteOwnAccount': False,
        'Accounts_AllowUserProfileChange': False,
        'Accounts_AllowUserAvatarChange': True,
        'Accounts_AllowRealNameChange': True,
        'Accounts_AllowEmailChange': False,
        'Accounts_AllowPasswordChange': False,
        # 'Accounts_AllowUserStatusMessageChange': True,
        'Accounts_AllowUsernameChange': False,
        'Accounts_Default_User_Preferences_sidebarGroupByType': True,
        'Accounts_Default_User_Preferences_sidebarShowUnread': True,
        'Accounts_ShowFormLogin': False,  # Should be set to True and single-synced for an admin to log in directly
        'Accounts_RegistrationForm': 'Disabled',
        'Accounts_RegistrationForm_LinkReplacementText': '',
        'Accounts_TwoFactorAuthentication_By_Email_Enabled': False,
        'Email_Changed_Email_Subject': 'Your email address has been changed',
        'Email_Changed_Email': "You have successfully changed your email address to [email]. If this change wasn't made by you or you think this was an error, please contact our support!",
        'Email_Footer': '</td></tr></table></div></td></tr></table><!-- /BODY --></td></tr><tr style="margin: 0; padding: 0;"><td style="margin: 0; padding: 0;"><!-- FOOTER --><table class="wrap"><tr><td class="container"><!-- content --><div class="content"><table width="100%%"><tr><td align="center"><h6>This email was sent to you from <a href="https://%(COSINNUS_PORTAL_URL)s">https://%(COSINNUS_PORTAL_URL)s</a></h6></td></tr></table></div><!-- /content --></td></tr></table><!-- /FOOTER --></td></tr></table></body></html>',
        'Accounts_Send_Email_When_Activating': False,
        'Accounts_Send_Email_When_Deactivating': False,
        'Accounts_Registration_AuthenticationServices_Enabled': False,
        'Accounts_TwoFactorAuthentication_Enforce_Password_Fallback': False,
        'Accounts_TwoFactorAuthentication_Enabled': False,
        # 'Device_Management_Enable_Login_Emails': False,  # removed, RockeChat made this a premium feature before 2025-12
        'Show_Setup_Wizard': False,
        # Layout
        'Layout_Home_Custom_Block_Visible': True,
        'Layout_Home_Body': """<p>Willkommen beim %(COSINNUS_BASE_PAGE_TITLE_TRANS)s Rocket.Chat!</p>

        <p>Schreibt private Nachrichten im Browser, per Smartphone- oder Desktop-App in Echtzeit an andere, in Projekten und Gruppen oder in eigenen Kanälen.</p>

        <p>Wenn du die App nach der Installation &ouml;ffnest, klicke auf <strong>Mit einem Server verbinden</strong>. Gebe im nachfolgenden Fenster folgende<strong> Serveradresse ein</strong>: <a href="%(COSINNUS_CHAT_BASE_URL)s" target="_blank" rel="nofollow noopener noreferrer">%(COSINNUS_CHAT_BASE_URL)s</a> und klicke auf <strong>Verbinden</strong>. Klicke auf <strong>Enter Chat</strong> und gib deine %(COSINNUS_BASE_PAGE_TITLE_TRANS)s Zugangsdaten in das sich &ouml;ffnende Fenster.</p>

            <p>Die Rocket.Chat-Desktops-Apps für Windows, MacOS und Linux stehen <a title="Rocket.Chat desktop apps" href="https://rocket.chat/download" target="_blank" rel="noopener">hier</a> zum Download bereit..</p>
            <p>Die native Mobile-App Rocket.Chat für Android und iOS ist bei <a title="Rocket.Chat+ on Google Play" href="https://play.google.com/store/apps/details?id=chat.rocket.android" target="_blank" rel="noopener">Google Play</a> und im  <a title="Rocket.Chat+ on the App Store" href="https://itunes.apple.com/app/rocket-chat/id1148741252" target="_blank" rel="noopener">App Store</a> erhältlich.</p>
            <p>Weitere Informationen finden Sie in der <a title="Rocket.Chat Documentation" href="https://rocket.chat/docs/" target="_blank" rel="noopener">Dokumentation</a>.</p>

        """,
        'Layout_Terms_of_Service': '<a href="https://wechange.de/cms/datenschutz/">Nutzungsbedingungen</a><br><a href="https://wechange.de/cms/datenschutz/">Datenschutz</a>',
        'Layout_Login_Terms': '',
        'Layout_Privacy_Policy': '<a href="https://wechange.de/cms/datenschutz/">Datenschutz</a>',
        # Disable default block on home page
        'theme-custom-css': """
            h2[data-qa-id="homepage-welcome-text"],
            h2[data-qa-id="homepage-welcome-text"] + h3,
            h2[data-qa-id="homepage-welcome-text"] + h3 + div.rcx-grid__wrapper  {
                display: none;
            }

            /* Increase logo size on login page */
            img[src="%(COSINNUS_CHAT_BASE_URL)s/assets/logo.png"],
            img[src="%(COSINNUS_CHAT_BASE_URL)s/assets/logo_dark.png"] {
                max-height: 6rem !important;
            }

            /* Hide "Welcome to XYZ workspace" and "By proceeding you are agreeing to our Terms of Service, Privacy Policy and Legal Notice. - Switch to en" on login page */
            div:has(> h1 > span#welcomeTitle) {
                display: none !important;
            }
            [aria-describedby="welcomeTitle"] + div {
                display: none !important;
            }
        """,
        # 'UI_Group_Channels_By_Type': False,
        'UI_Use_Real_Name': True,
        # Rate Limiter
        'API_Enable_Rate_Limiter_Limit_Calls_Default': 10000,
        # Nachrichten
        'API_Embed': False,
        'Hide_System_Messages': ['uj', 'ul', 'ru', 'subscription-role-added', 'ut', 'subscription-role-removed', 'au'],
        # User Surveys
        'NPS_survey_enabled': False,
        # Disable update check notifications
        'Update_EnableChecker': False,
        # Custom login script copying the Rocketchat session cookies to the top level domain. This makes the cookies
        # available in the logout view and is used to log out the user from the Rocketchat session.
        'Custom_Script_Logged_In': """
            setTimeout(function() {
                const rcUid = document.cookie.split("; ").find((row) => row.startsWith("rc_uid="))?.split("=")[1];
                const rcToken = document.cookie.split("; ").find((row) => row.startsWith("rc_token="))?.split("=")[1];
                document.cookie = 'rc_session_uid=' + rcUid + ';domain=%(COSINNUS_CHAT_SESSION_COOKIE_DOMAIN)s;path=/';
                document.cookie = 'rc_session_token=' + rcToken + ';domain=%(COSINNUS_CHAT_SESSION_COOKIE_DOMAIN)s;path=/';
            }, 1000);
        """,
        # TODO: this setting needs to be added, but under API url:
        #    https://chat.<server>/api/v1/method.call/authorization:removeRoleFromPermission
        # 'authorization:removeRoleFromPermission': ["add-user-to-joined-room","moderator"],
    }

    COSINNUS_CHAT_SYNC_OAUTH_SETTINGS = {
        'Accounts_OAuth_Custom-%(portal_name_cap)s': True,
        'Accounts_OAuth_Custom-%(portal_name_cap)s-url': '%(portal_domain)s',
        'Accounts_OAuth_Custom-%(portal_name_cap)s-token_path': '/o/token/',
        'Accounts_OAuth_Custom-%(portal_name_cap)s-token_sent_via': 'header',
        'Accounts_OAuth_Custom-%(portal_name_cap)s-identity_path': '/o/me/',
        'Accounts_OAuth_Custom-%(portal_name_cap)s-authorize_path': '/o/authorize/',
        'Accounts_OAuth_Custom-%(portal_name_cap)s-scope': 'read',
        'Accounts_OAuth_Custom-%(portal_name_cap)s-id': '%(oauth_id)s',
        'Accounts_OAuth_Custom-%(portal_name_cap)s-secret': '%(oauth_secret)s',
        'Accounts_OAuth_Custom-%(portal_name_cap)s-button_label_text': 'Enter chat',
        'Accounts_OAuth_Custom-%(portal_name_cap)s-merge_users': True,
    }
    COSINNUS_CHAT_USER = None
    COSINNUS_CHAT_PASSWORD = None

    # rocket authentication timeout is 30 days  by default
    COSINNUS_CHAT_CONNECTION_CACHE_TIMEOUT = 60 * 60 * 24 * 30

    # enables the read-only mode for the legacy postman messages system and shows an
    # "archived messages button" in the user profile
    COSINNUS_POSTMAN_ARCHIVE_MODE = False
