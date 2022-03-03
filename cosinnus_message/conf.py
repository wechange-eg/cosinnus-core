# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import object
from django.conf import settings  # noqa
from django.utils.translation import ugettext_lazy as _

from appconf import AppConf


class CosinnusMessageConf(AppConf):
    pass


class CosinnusMessageDefaultSettings(AppConf):
    """ Settings without a prefix namespace to provide default setting values for other apps.
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
    
    COSINNUS_CHAT_BASE_URL = None
    
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
    # the introductory explanation message for the users in a "Contact Group" room
    COSINNUS_ROCKET_GROUP_CONTACT_ROOM_INFO_MESSAGE = _('Please post your request or question here. You can see the channel members by clicking the group icon at the top of the channel.')
    
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
        'Accounts_ShowFormLogin': False,  # Required to be able to login as bot on first deployment
        'Accounts_RegistrationForm': 'Disabled',
        'Accounts_RegistrationForm_LinkReplacementText': '',
        'Accounts_TwoFactorAuthentication_By_Email_Enabled': False,
        'Email_Changed_Email_Subject': 'Your Registration has been received',
        'Email_Changed_Email': 'Thank you for signing up. Your E-Mail validation link will arrive shortly.',
        'Accounts_Send_Email_When_Activating': False,
        'Accounts_Send_Email_When_Deactivating': False,
        'Accounts_Registration_AuthenticationServices_Enabled': False,
        'Accounts_TwoFactorAuthentication_Enforce_Password_Fallback': False,
        'Accounts_TwoFactorAuthentication_Enabled': False,

        # Layout
        'Layout_Home_Body': '''<p>Willkommen beim %(COSINNUS_BASE_PAGE_TITLE_TRANS)s Rocket.Chat!</p>

        <p>Schreibt private Nachrichten im Browser, per Smartphone- oder Desktop-App in Echtzeit an andere, in Projekten und Gruppen oder in eigenen Kanälen.</p>
        
        <p>Wenn du die App nach der Installation &ouml;ffnest, klicke auf <strong>Mit einem Server verbinden</strong>. Gebe im nachfolgenden Fenster folgende<strong> Serveradresse ein</strong>: <a href="%(COSINNUS_CHAT_BASE_URL)s" target="_blank" rel="nofollow noopener noreferrer">%(COSINNUS_CHAT_BASE_URL)s</a> und klicke auf <strong>Verbinden</strong>. Klicke auf <strong>Enter Chat</strong> und gib deine %(COSINNUS_BASE_PAGE_TITLE_TRANS)s Zugangsdaten in das sich &ouml;ffnende Fenster.</p>
        
            <p>Die Rocket.Chat-Desktops-Apps für Windows, MacOS und Linux stehen <a title="Rocket.Chat desktop apps" href="https://rocket.chat/download" target="_blank" rel="noopener">hier</a> zum Download bereit..</p>
            <p>Die native Mobile-App Rocket.Chat für Android und iOS ist bei <a title="Rocket.Chat+ on Google Play" href="https://play.google.com/store/apps/details?id=chat.rocket.android" target="_blank" rel="noopener">Google Play</a> und im  <a title="Rocket.Chat+ on the App Store" href="https://itunes.apple.com/app/rocket-chat/id1148741252" target="_blank" rel="noopener">App Store</a> erhältlich.</p>
            <p>Weitere Informationen finden Sie in der <a title="Rocket.Chat Documentation" href="https://rocket.chat/docs/" target="_blank" rel="noopener">Dokumentation</a>.</p>
            
        ''',
        'Layout_Terms_of_Service': '<a href="https://wechange.de/cms/datenschutz/">Nutzungsbedingungen</a><br><a href="https://wechange.de/cms/datenschutz/">Datenschutz</a>',
        'Layout_Login_Terms': '',
        'Layout_Privacy_Policy': '<a href="https://wechange.de/cms/datenschutz/">Datenschutz</a>',
        # 'UI_Group_Channels_By_Type': False,
        'UI_Use_Real_Name': True,

        # Rate Limiter
        'API_Enable_Rate_Limiter_Limit_Calls_Default': 10000,

        # Nachrichten
        'API_Embed': False,
        'Hide_System_Messages': ["uj","ul","ru","subscription-role-added","ut","subscription-role-removed","au"],
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
    