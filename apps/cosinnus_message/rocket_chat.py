import logging
import mimetypes
import os
import re
import secrets

from cosinnus.models.group_extra import CosinnusSociety, CosinnusProject,\
    CosinnusConference
from cosinnus.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext_lazy as _
from oauth2_provider.models import Application

from rocketchat_API.APIExceptions.RocketExceptions import RocketAuthenticationException,\
    RocketConnectionException
from rocketchat_API.rocketchat import RocketChat as RocketChatAPI
from cosinnus.models.group import CosinnusPortal, CosinnusGroupMembership
from cosinnus.models import MEMBERSHIP_ADMIN
from cosinnus.models.membership import MEMBERSHIP_MEMBER,\
    MEMBERSHIP_INVITED_PENDING, MEMBERSHIP_PENDING, MEMBER_STATUS
from cosinnus.models.profile import PROFILE_SETTING_ROCKET_CHAT_ID, PROFILE_SETTING_ROCKET_CHAT_USERNAME
import traceback
from cosinnus.utils.user import filter_active_users, filter_portal_users
import six
from annoying.functions import get_object_or_None
from cosinnus_message.utils.utils import save_rocketchat_mail_notification_preference_for_user_setting
from cosinnus.templatetags.cosinnus_tags import full_name
from django.template.defaultfilters import truncatewords

logger = logging.getLogger(__name__)

ROCKETCHAT_USER_CONNECTION_CACHE_KEY = 'cosinnus/core/portal/%d/rocketchat-user-connection/%s/'

ROCKETCHAT_NOTE_ID_SETTINGS_KEY = 'rocket_chat_message_id'

ROCKETCHAT_PREFERENCE_EMAIL_NOTIFICATION_OFF = 'nothing'
ROCKETCHAT_PREFERENCE_EMAIL_NOTIFICATION_DEFAULT = 'default'
ROCKETCHAT_PREFERENCE_EMAIL_NOTIFICATION_MENTIONS = 'mentions'
ROCKETCHAT_PREFERENCES_EMAIL_NOTIFICATION = (
    ROCKETCHAT_PREFERENCE_EMAIL_NOTIFICATION_OFF,
    ROCKETCHAT_PREFERENCE_EMAIL_NOTIFICATION_DEFAULT,
    ROCKETCHAT_PREFERENCE_EMAIL_NOTIFICATION_MENTIONS
)

def get_cached_rocket_connection(rocket_username, password, server_url, reset=False):
    """ Retrieves a cached rocketchat connection or creates a new one and caches it.
        @param reset: Resets the cached connection and connects a fresh one immediately """
    cache_key = ROCKETCHAT_USER_CONNECTION_CACHE_KEY % (CosinnusPortal.get_current().id, rocket_username)

    if reset:
        cache.delete(cache_key)
        rocket_connection = None
    else:
        rocket_connection = cache.get(cache_key)
        # check if rocket connection is still alive, if not, remove it from cache
        alive = False
        try:
            alive = rocket_connection.me().status_code == 200
        except:
            pass
        if not alive:
            cache.delete(cache_key)
            rocket_connection = None

    if rocket_connection is None:
        rocket_connection = RocketChat(user=rocket_username, password=password, server_url=server_url)
        cache.set(cache_key, rocket_connection, settings.COSINNUS_CHAT_CONNECTION_CACHE_TIMEOUT)
    return rocket_connection


def delete_cached_rocket_connection(rocket_username):
    """ Deletes a cached rocketchat connection or creates a new one and caches it """
    cache_key = ROCKETCHAT_USER_CONNECTION_CACHE_KEY % (CosinnusPortal.get_current().id, rocket_username)
    cache.delete(cache_key)


class RocketChat(RocketChatAPI):

    def __init__(self, *args, **kwargs):
        # this fixes the re-used dict from the original rocket API object
        self.headers = {}
        super(RocketChat, self).__init__(*args, **kwargs)

    def rooms_upload(self, rid, file, **kwargs):
        """
        Overwrite base method to allow filename and mimetye kwargs
        """
        filename = kwargs.pop('filename', os.path.basename(file))
        mimetype = kwargs.pop('mimetype', mimetypes.guess_type(file)[0])
        files = {
            'file': (filename, open(file, 'rb'), mimetype),
        }
        return self.__call_api_post('rooms.upload/' + rid, kwargs=kwargs, use_json=False, files=files)


class RocketChatConnection:

    rocket = None
    stdout, stderr = None, None
    
    def __init__(self, user=settings.COSINNUS_CHAT_USER, password=settings.COSINNUS_CHAT_PASSWORD,
                 url=settings.COSINNUS_CHAT_BASE_URL, stdout=None, stderr=None):
        # get a cached version of the rocket connection
        self.rocket = get_cached_rocket_connection(user, password, url)

        if stdout:
            self.stdout = stdout
        if stderr:
            self.stderr = stderr

    def oauth_sync(self):
        """ Note: this requires an Oauth app having been created in rocketchat manually,
            by the name of the portal identifier name """
        client_id = secrets.token_urlsafe(16)
        client_secret = secrets.token_urlsafe(16)
        # create django oauth toolkit provider app
        portal_id = CosinnusPortal.get_current().id
        app, __ = Application.objects.get_or_create(name=f"rocketchat_{portal_id}")
        app.client_id = client_id
        app.client_secret = client_secret
        app.redirect_uris = f"{self.rocket.server_url}/_oauth/{settings.COSINNUS_PORTAL_NAME}"
        app.client_type = Application.CLIENT_CONFIDENTIAL
        app.authorization_grant_type = Application.GRANT_AUTHORIZATION_CODE
        app.skip_authorization = True
        app.save()
            
        values_dict = {
            'portal_name_cap': settings.COSINNUS_PORTAL_NAME.capitalize(),
            'portal_domain': CosinnusPortal.get_current().get_domain(),
            'oauth_id': client_id,
            'oauth_secret': client_secret,
        }
        for setting, value in settings.COSINNUS_CHAT_SYNC_OAUTH_SETTINGS.items():
            if type(value) in six.string_types:
                value = value % values_dict
            if type(setting) in six.string_types:
                setting = setting % values_dict
            response = self.rocket.settings_update(setting, value).json()
            if not response.get('success'):
                self.stderr.write('ERROR! ' + str(setting) + ': ' + str(value) + ':: ' + str(response))
            else:
                self.stdout.write('OK! ' + str(setting) + ': ' + str(value)) 
        

    def settings_update(self):
        for setting, value in settings.COSINNUS_CHAT_SETTINGS.items():
            if type(value) in six.string_types:
                value = value % settings.__dict__['_wrapped'].__dict__
            response = self.rocket.settings_update(setting, value).json()
            if not response.get('success'):
                self.stderr.write('ERROR! ' + str(setting) + ': ' + str(value) + ':: ' + str(response))
            else:
                self.stdout.write('OK! ' + str(setting) + ': ' + str(value)) 
    
    def create_missing_users(self, skip_inactive=False, force_group_membership_sync=False):
        """ 
        Create missing user accounts in rocketchat (and verify that ones with an existing
        connection still exist in rocketchat properly).
        Inactive user accounts and ones that never logged in will also be created.
        Will never create accounts for users with __unverified__ emails.
            
        @param skip_inactive: if True, will not create any accounts for inactive users
        @param force_group_membership_sync: if True, will also re-do and sync all group
            memberships, for all users. (default: only sync memberships for users created 
            during this run)
        """
        users = filter_portal_users(get_user_model().objects.all())
        users = users.exclude(email__startswith='__unverified__') # accounts with a real mail but unverified flag will be created
        if skip_inactive:
            users = filter_active_users(users)
        count = len(users)
        for i, user in enumerate(users):
            result = self.ensure_user_account_sanity(user, force_group_membership_sync=force_group_membership_sync)
            self.stdout.write('User %i/%i. Success: %s \t %s' % (i, count, str(result), user.email),)

    def users_sync(self, skip_update=False):
        """
        Sync active users that have already been created in rocketchat.
        Will not create new users.
        @param skip_update: if True, skips updating existing users
        :return:
        """
        # Get existing rocket users
        rocket_users = {}
        rocket_emails_usernames = {}
        size = 100
        offset = 0
        while True:
            response = self.rocket.users_list(size=size, offset=offset).json()
            if not response.get('success'):
                self.stderr.write('users_sync: ' + str(response), response)
                break
            if response['count'] == 0:
                break

            for rocket_user in response['users']:
                rocket_users[rocket_user['username']] = rocket_user
                for email in rocket_user.get('emails', []):
                    if not email.get('address'):
                        continue
                    rocket_emails_usernames[email['address']] = rocket_user['username']
            offset += response['count']

        # Check active users in DB
        users = filter_active_users(filter_portal_users(get_user_model().objects.all()))
        
        count = len(users)
        for i, user in enumerate(users):
            self.stdout.write('User %i/%i' % (i, count), ending='\r')
            self.stdout.flush()

            if not hasattr(user, 'cosinnus_profile'):
                return
            profile = user.cosinnus_profile
            rocket_username = profile.rocket_username

            rocket_user = rocket_users.get(rocket_username)

            # User with different username but same email address exists?
            if not rocket_user and profile.rocket_user_email in rocket_emails_usernames.keys():
                # Change username in DB
                rocket_username = rocket_emails_usernames.get(profile.rocket_user_email)
                rocket_user = rocket_users.get(rocket_username)

                profile.settings[PROFILE_SETTING_ROCKET_CHAT_USERNAME] = rocket_username
                profile.save(update_fields=['settings'])

            # Username exists?
            if rocket_user:
                if skip_update:
                    continue
                
                changed = False
                # TODO: Introducing User.updated_at would improve performance here
                rocket_emails = (e['address'] for e in rocket_user.get('emails'))
                # Email address changed?
                if profile.rocket_user_email not in rocket_emails:
                    changed = True
                # Name changed?
                elif profile.get_external_full_name() != rocket_user.get('name'):
                    changed = True
                elif rocket_username != rocket_user.get('username'):
                    changed = True
                # Avatar changed?
                else:
                    rocket_avatar_url = self.rocket.users_get_avatar(username=rocket_username)
                    profile_avatar_url = user.cosinnus_profile.avatar.url if user.cosinnus_profile.avatar else ""
                    if profile_avatar_url != rocket_avatar_url:
                        changed = True
                if changed:
                    self.users_update(user)

            else:
                self.users_create(user)

    def groups_sync(self):
        """
        Sync groups
        :return:
        """
        portal = CosinnusPortal.get_current()
        
        # Sync WECHANGE groups
        for group_model in (CosinnusConference, CosinnusSociety, CosinnusProject):
            groups = group_model.objects.filter(is_active=True, portal=portal)
            
            
            count = len(groups)
            for i, group in enumerate(groups):
                self.stdout.write('%s %i/%i' % (str(group_model), i, count), ending='\r')
                self.stdout.flush()
                self.groups_create(group)


    def get_user_id(self, user):
        """
        Returns Rocket.Chat ID from user settings or Rocket.Chat API
        :param user:
        :return:
        """
        if not hasattr(user, 'cosinnus_profile'):
            return
        profile = user.cosinnus_profile
        if not profile.settings.get(PROFILE_SETTING_ROCKET_CHAT_ID):
            username = profile.settings.get(PROFILE_SETTING_ROCKET_CHAT_USERNAME)
            if not username:
                logger.error('RocketChat: get_user_id: no username given')
                return
            response = self.rocket.users_info(username=username).json()
            if not response.get('success'):
                logger.exception('get_user_id: ' + str(response.get('errorType', '<No Error Type>')), extra={'trace': traceback.format_stack(), 'username': username, 'response': response})
                return
            user_data = response.get('user')
            rocket_chat_id = user_data.get('_id')
            profile.settings[PROFILE_SETTING_ROCKET_CHAT_ID] = rocket_chat_id
            # Update profile settings without triggering signals to prevent cycles
            type(profile).objects.filter(pk=profile.pk).update(settings=profile.settings)
        return profile.settings.get(PROFILE_SETTING_ROCKET_CHAT_ID)

    def get_group_id(self, group, room_key=None):
        """
        Returns Rocket.Chat ID from group settings or Rocket.Chat API
        :param user:
        :return:
        """
        room_key = room_key or settings.COSINNUS_ROCKET_GROUP_ROOM_KEYS[0]
        room_name_code = settings.COSINNUS_ROCKET_GROUP_ROOM_NAMES_MAP[room_key]
        # if the group doesn't have a room id in its settings, try to find the room by name
        key = f'{PROFILE_SETTING_ROCKET_CHAT_ID}_{room_key}'
        if not group.settings.get(key):
            group_name = room_name_code % group.slug
            response = self.rocket.groups_info(room_name=group_name).json()
            if not response.get('success'):
                logger.error('RocketChat: get_group_id ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
                return
            group_data = response.get('group')
            rocket_chat_id = group_data.get('_id')
            group.settings[key] = rocket_chat_id
            # Update group settings without triggering signals to prevent cycles
            type(group).objects.filter(pk=group.pk).update(settings=group.settings)
        return group.settings.get(key)

    def users_create_or_update(self, user, request=None):
        if not hasattr(user, 'cosinnus_profile'):
            return
        if PROFILE_SETTING_ROCKET_CHAT_ID in user.cosinnus_profile.settings:
            return self.users_update(user, request)
        else:
            return self.users_create(user, request)

    def users_create(self, user, request=None):
        """
        Create user with name, email address and avatar
        :return: A user object if the creation was done without errors.
        """
        if not hasattr(user, 'cosinnus_profile'):
            return
        if not user.email or '__unverified__' in user.email:
            return
        profile = user.cosinnus_profile
        original_password = user.password
        rocket_user_password = user.password or get_random_string(length=16)
        data = {
            "email": profile.rocket_user_email,
            "name": profile.get_external_full_name() or str(user.id),
            "password": rocket_user_password,
            "username": profile.rocket_username,
            "bio": profile.get_absolute_url(),
            "active": user.is_active,
            "verified": True, # we keep verified at True always and provide a fake email for unverified accounts, since rocket is broken and still sends emails to unverified accounts
            "requirePasswordChange": False,
        }
        response = self.rocket.users_create(**data).json()
        if not response.get('success'):
            logger.error('RocketChat: users_create: ' + response.get('errorType', '<No Error Type>'), extra={'response': response})

        # Save Rocket.Chat User ID to user instance
        user_id = response.get('user', {}).get('_id')
        profile = user.cosinnus_profile
        profile.settings[PROFILE_SETTING_ROCKET_CHAT_ID] = user_id
        # Update profile settings without triggering signals to prevent cycles
        type(profile).objects.filter(pk=profile.pk).update(settings=profile.settings)
        user.cosinnus_profile = profile
        
        # Update the user's email preferences based on the portal default
        # Hack: since the user object might have a null password on creation, we give the user object a temporary password, 
        # because otherwise the rocket user connection would not be able to log in. 
        # Note: the user should not be saved in between this! if it it ever does, 
        # we have to re-save the user afterwards with the original password
        user.password = rocket_user_password
        save_rocketchat_mail_notification_preference_for_user_setting(user, settings.COSINNUS_DEFAULT_ROCKETCHAT_NOTIFICATION_SETTING)
        user.password = original_password
        return user

    def users_update_username(self, rocket_username, user):
        """
        Updates username
        :return:
        """
        # Get user ID
        if not hasattr(user, 'cosinnus_profile'):
            return
        profile = user.cosinnus_profile
        if not profile.settings.get(PROFILE_SETTING_ROCKET_CHAT_ID):
            response = self.rocket.users_info(username=rocket_username).json()
            if not response.get('success'):
                logger.error('RocketChat: get_user_id ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
                return
            user_data = response.get('user')
            user_id = user_data.get('_id')
            profile.settings[PROFILE_SETTING_ROCKET_CHAT_ID] = user_id
            # Update profile settings without triggering signals to prevent cycles
            type(profile).objects.filter(pk=profile.pk).update(settings=profile.settings)
        user_id = profile.settings[PROFILE_SETTING_ROCKET_CHAT_ID]
        if not user_id:
            return

        # Update username
        response = self.rocket.users_update(user_id=user_id, username=profile.rocket_username).json()
        if not response.get('success'):
            logger.error('RocketChat: users_update_username: ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
    
    def check_user_account_status(self, user):
        """ Read-only check whether or not the user exists in rocket chat.
            @return:   True if the user account exists.
                        False if the user account definitely does not exist.
                        None if another error occurred or was returned, or the service was unavailable. """
        user_id = self.get_user_id(user)
        if not user_id:
            return False
        else:
            response = self.rocket.users_info(user_id=user_id)
            if response.status_code == 200 and response.json().get('success', False) and response.json().get('user', None):
                # user account is healthy
                return True
            elif response.status_code == 400 and response.json().get('error', '').lower() == 'user not found.':
                return False
            else:
                logger.info('Rocketchat check_user_account_status: users_info response returned a status code or error message we could not interpret.',
                    extra={'response-text': response.text, 'response_code': response.status_code})
                return None
    
    def ensure_user_account_sanity(self, user, force_group_membership_sync=False):
        """ A helper function that can always be safely called on any user object.
            Checks if the user account exists.
            @param force_group_membership_sync: if True, will also re-do group memberships for active users
                instead of only for freshly created accounts
            @param return: True if the account was either healthy or was newly created. False (and causes logs) otherwise """
        if not hasattr(user, 'cosinnus_profile'):
            # just return here, appearently this is a special/corrupted user account
            logger.error('RocketChat: Could not perform ensure_user_account_sanity: User object has no CosinnusProfile!', extra={'user_id': getattr(user, 'id', None)})
            return None
        
        # check for False, as None would mean unknown status
        status = self.check_user_account_status(user)
        if status is False:
            user = self.users_create(user)
            # re-check again to make sure the user was actually created
            if user and self.check_user_account_status(user):
                logger.info('ensure_user_account_sanity successfully created new rocketchat user account', extra={'user_id': getattr(user, 'id', None)})
                # newly created user, do a invite to their group memberships' rooms
                self.force_redo_user_room_memberships(user)
                return True
            else:
                logger.info('ensure_user_account_sanity attempted to create a new rocketchat user account, but failed!', extra={'user_id': getattr(user, 'id', None)})
                return False
        elif status is None:
            logger.error('RocketChat: ensure_user_account_sanity was called, but could not do anything as `check_user_account_status` received an unknown status code.')
            return False
        
        # status is True, account exists
        if force_group_membership_sync:
            self.force_redo_user_room_memberships(user)
        return True
    
    def force_redo_user_room_membership_for_group(self, user, group):
        """ A helper function that will re-do all room memberships by
            saving each user's membership (and having the invite-room hooks trigger) """
        membership = get_object_or_None(CosinnusGroupMembership, group__portal=CosinnusPortal.get_current(), user=user, group=group)
        if membership:
            # force the re-invite
            self.invite_or_kick_for_membership(membership)
    
    def force_redo_user_room_memberships(self, user):
        """ A helper function that will re-do all room memberships by
            saving each user's membership (and having the invite-room hooks trigger) """
        for membership in CosinnusGroupMembership.objects.filter(group__portal=CosinnusPortal.get_current(), user=user):
            # force the re-invite
            self.invite_or_kick_for_membership(membership)
            # saving causes conference room memberships to be re-done
            membership.save()
    
    def users_update(self, user, request=None, force_user_update=False, update_password=False):
        """
        Updates user name, email address and avatar
        :return:
        """
        user_id = self.get_user_id(user)
        if not user_id:
            return
        if not hasattr(user, 'cosinnus_profile'):
            return

        # Get user information and ID
        response = self.rocket.users_info(user_id=user_id)
        if not response.status_code == 200:
            logger.error('RocketChat: users_info status code: ' + str(response.text), extra={'response': response})
            return
        response = response.json()
        if not response.get('success'):
            logger.error('RocketChat: users_info response: ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
            return
        user_data = response.get('user')

        # Update name, email address, password, verified status if they have changed
        profile = user.cosinnus_profile
        rocket_email = user_data.get('emails', [{}])[0].get('address', None)
        #rocket_mail_verified = user_data.get('emails', [{}])[0].get('verified', None)
        if force_user_update or user_data.get('name') != profile.get_external_full_name() or rocket_email != profile.rocket_user_email:
            data = {
                "username": profile.rocket_username,
                "name": profile.get_external_full_name(),
                "email": profile.rocket_user_email,
                "bio": profile.get_absolute_url(),
                "active": user.is_active,
                "verified": True, # we keep verified at True always and provide a fake email for unverified accounts, since rocket is broken and still sends emails to unverified accounts
                "requirePasswordChange": False,
            }
            # updating the password invalidates existing user sessions, so use it only
            # when actually needed
            if update_password:
                data.update({
                    "password": user.password,
                })
            response = self.rocket.users_update(user_id=user_id, **data).json()
            if not response.get('success'):
                logger.error(f'users_update (force={force_user_update}) base user: ' + response.get('errorType', '<No Error Type>'), extra={'response': response})

        # Update Avatar URL
        avatar_url = user.cosinnus_profile.avatar.url if user.cosinnus_profile.avatar else ''
        if avatar_url:
            if request:
                avatar_url = request.build_absolute_uri(avatar_url)
            else:
                portal_domain = CosinnusPortal.get_current().get_domain()
                avatar_url = f'{portal_domain}{avatar_url}'
            response = self.rocket.users_set_avatar(avatar_url, userId=user_id).json()
            if not response.get('success'):
                logger.error(f'users_update (force={force_user_update}) avatar: ' + response.get('errorType', '<No Error Type>'), extra={'response': response})

    def users_disable(self, user):
        """
        Set user to inactive
        :return:
        """
        user_id = self.get_user_id(user)
        if not user_id:
            return
        data = {
            "active": False,
        }
        response = self.rocket.users_update(user_id=user_id, **data).json()
        if not response.get('success'):
            logger.error('RocketChat: users_disable: ' + response.get('errorType', '<No Error Type>'), extra={'response': response})

    def users_enable(self, user):
        """
        Set user to active
        :return:
        """
        user_id = self.get_user_id(user)
        if not user_id:
            return
        data = {
            "active": True,
        }
        response = self.rocket.users_update(user_id=user_id, **data).json()
        if not response.get('success'):
            logger.error('RocketChat: users_enable: ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
    
    def users_delete(self, user):
        """
        Delete a user
        :return:
        """
        user_id = self.get_user_id(user)
        if not user_id:
            return
        response = self.rocket.users_delete(user_id=user_id, confirmRelinquish=True).json()
        if not response.get('success'):
            logger.error('RocketChat: users_delete: ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
    
    def get_group_room_name(self, group, room_key=None):
        """ Returns the rocketchat room name for a CosinnusGroup, for use in any URLs.
            Creates a room for the group if it doesn't exist yet """
        room_key = room_key or settings.COSINNUS_ROCKET_GROUP_ROOM_KEYS[0]
        room_id = group.settings.get(f'{PROFILE_SETTING_ROCKET_CHAT_ID}_{room_key}', None)
        # create group if it didn't exist
        if not room_id:
            self.groups_create(group)
            room_id = group.settings.get(f'{PROFILE_SETTING_ROCKET_CHAT_ID}_{room_key}', None)
        response = self.rocket.groups_info(room_id=room_id).json()
        if not response.get('success'):
            logger.error('RocketChat: groups_request: groups_info ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
            return None
        group_name = response.get('group', {}).get('name', None)
        return group_name
    
    def groups_request(self, group, user, force_sync_membership=False):
        """
        Returns name of group if user is member of group, otherwise creates private group for group request
        (with user and group admins as members) and returns group name
        :param group:
        :param user:
        :param force_sync_membership: if True, and the user is a member of the CosinnusGroup,
            the user will be added to the rocketchat group again (useful to make sure
            that users are *really* members of the group)
        :return:
        """
        group_name = ''
        if group.is_member(user):
            group_name = self.get_group_room_name(group)
            if force_sync_membership:
                self.force_redo_user_room_membership_for_group(user, group)
        else:
            # Create private group
            group_name = f'{group.slug}-{get_random_string(7)}'
            if not hasattr(user, 'cosinnus_profile'):
                return
            profile = user.cosinnus_profile
            members = [u.cosinnus_profile.rocket_username for u in group.actual_admins] + [profile.rocket_username, ]
            response = self.rocket.groups_create(group_name, members=members).json()
            if not response.get('success'):
                logger.error('RocketChat: groups_request: groups_create ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
            group_name = response.get('group', {}).get('name')
            room_id = response.get('group', {}).get('_id')

            # Make user moderator of group
            user_id = user.cosinnus_profile.settings.get(PROFILE_SETTING_ROCKET_CHAT_ID)
            if user_id:
                response = self.rocket.groups_add_moderator(room_id=room_id, user_id=profile.rocket_username).json()
                if not response.get('success'):
                    logger.error('RocketChat: groups_request: groups_add_moderator ' + response.get('errorType', '<No Error Type>'), extra={'response': response})

            # Set description of group
            topic = group.trans.CONTACT_ROOM_TOPIC % {'group_name': group.name}
            topic = f'{topic} ({group.get_absolute_url()})'
            response = self.rocket.groups_set_topic(room_id=room_id, topic=topic).json()
            if not response.get('success'):
                logger.error('RocketChat: groups_request: groups_set_topic ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
                
            # Post help message
            greeting_message = group.trans.CONTACT_ROOM_GREETING_MESSAGE
            info_message = settings.COSINNUS_ROCKET_GROUP_CONTACT_ROOM_INFO_MESSAGE
            message = f'@{profile.rocket_username} @all {greeting_message} {info_message}'
            response = self.rocket.chat_post_message(text=message, room_id=room_id).json()
            if not response.get('success'):
                logger.error('RocketChat: groups_request: chat_post_message ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
                
        return group_name

    def create_private_room(self, group_name, moderator_user, member_users=None, additional_admin_users=None):
        """ Create a private group with a user as first member and moderator.
            @param moderator_user: user who will become both a member and moderator
            @param member_users: list of users who become members. may contain the moderator_user again
            @return: the rocketchat room_id """
        if not hasattr(moderator_user, 'cosinnus_profile'):
            return
        # create group
        member_users = member_users or []
        members = [moderator_user.cosinnus_profile.rocket_username, ] + [member.cosinnus_profile.rocket_username for member in member_users]
        members = list(set(members))
        response = self.rocket.groups_create(group_name, members=members).json()
        if not response.get('success'):
            logger.error('RocketChat: Direct create_private_group groups_create', extra={'response': response})
        group_name = response.get('group', {}).get('name')
        room_id = response.get('group', {}).get('_id')

        # Make user moderator of group
        admin_users = list(additional_admin_users) if additional_admin_users else []
        admin_users.append(moderator_user)
        admin_users = list(set(admin_users))
        for admin_user in admin_users:
            user_id = admin_user.cosinnus_profile.settings.get(PROFILE_SETTING_ROCKET_CHAT_ID)
            if user_id:
                response = self.rocket.groups_add_moderator(room_id=room_id, user_id=user_id).json()
                if not response.get('success'):
                    logger.error('RocketChat: Direct create_private_group groups_add_moderator', extra={'response': response})
        return room_id

    def groups_create(self, group):
        """
        Create default channels for group or project or conference, if they doesn't exist yet:
        1. #slug-general: Private group with all members
        2. #slug-news: Private ready-only group with all members, new notes appear here.
        :param group:
        :return:
        """
        memberships = group.memberships.select_related('user', 'user__cosinnus_profile')
        admin_qs = memberships.filter_membership_status(MEMBERSHIP_ADMIN)
        admin_ids = [self.get_user_id(m.user) for m in admin_qs]
        members_qs = memberships.filter_membership_status(MEMBER_STATUS)
        member_usernames = [str(m.user.cosinnus_profile.rocket_username)
                            for m in members_qs if m.user.cosinnus_profile]
        member_usernames.append(settings.COSINNUS_CHAT_USER)

        # Createconfigured channels
        for group_room_key, room_name_code in settings.COSINNUS_ROCKET_GROUP_ROOM_NAMES_MAP.items():
            # check if group room exists
            room_id = group.settings.get(f'{PROFILE_SETTING_ROCKET_CHAT_ID}_{group_room_key}', None)
            if room_id:
                response = self.rocket.groups_info(room_id=room_id).json()
                if response.get('success'):
                    # room existed, don't create
                    continue
            
            group_name = room_name_code % group.slug
            response = self.rocket.groups_create(name=group_name, members=member_usernames).json()
            
            if not response.get('success'):
                # Duplicate group name?
                if response.get('errorType') == 'error-duplicate-channel-name':
                    # Assign Rocket.Chat group ID to WECHANGE group
                    response = self.rocket.groups_info(room_name=group_name).json()
                    if not response.get('success'):
                        logger.error('RocketChat: groups_create: groups_info ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
                    room_id = response.get('group', {}).get('_id')
                    if room_id:
                        # Update group settings without triggering signals to prevent cycles
                        group.settings[f'{PROFILE_SETTING_ROCKET_CHAT_ID}_{group_room_key}'] = room_id
                        type(group).objects.filter(pk=group.pk).update(settings=group.settings)
                    continue
                elif response.get('errorType') in ('error-room-archived', 'error-archived-duplicate-name'):
                    # group has an archived room, which is probably a different one
                    # we rename the old room to a random one, leave it archived, and create the new room properly
                    old_room_id = self.get_group_id(group, room_key=group_room_key)
                    if old_room_id:
                        random_room_name = group_name + '-' + get_random_string(6)
                        # we need to unarchive the room to rename it
                        response = self.rocket.groups_unarchive(room_id=old_room_id).json()
                        if not response.get('success'):
                            logger.error('RocketChat: groups_unarchive (groups_create archive deduplication) ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
                            continue
                        response = self.rocket.groups_rename(room_id=old_room_id, name=random_room_name).json()
                        if not response.get('success'):
                            logger.error('RocketChat: groups_rename (groups_create archive deduplication) ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
                            continue
                        response = self.rocket.groups_archive(room_id=old_room_id).json()
                        if not response.get('success'):
                            logger.error('RocketChat: groups_archive (groups_create archive deduplication) ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
                            continue
                        # if successfully renamed, we're free to try to create out new room again
                        response = self.rocket.groups_create(name=group_name, members=member_usernames).json()
                        # if successful, we let this run into the regular group-setting room name assignment
                        if not response.get('success'):
                            logger.error('RocketChat: groups_rename (groups_create archive deduplication) ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
                            continue
                else:
                    logger.error('RocketChat: groups_create ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
            
            if response.get('success'):
                room_id = response.get('group', {}).get('_id')
                if room_id:
                    # Add moderators
                    for user_id in admin_ids:
                        response = self.rocket.groups_add_moderator(room_id=room_id, user_id=user_id).json()
                        if not response.get('success'):
                            logger.error('RocketChat: groups_create: groups_add_moderator ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
                    # Update group settings without triggering signals to prevent cycles
                    group.settings[f'{PROFILE_SETTING_ROCKET_CHAT_ID}_{group_room_key}'] = room_id
                    type(group).objects.filter(pk=group.pk).update(settings=group.settings)
    
                    # Set description
                    response = self.rocket.groups_set_description(room_id=room_id, description=group.name).json()
                    if not response.get('success'):
                        logger.error('RocketChat: groups_create: groups_set_description ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
                    
                    # Set topic to plattform group URL as backlink
                    self.group_set_topic_to_url(group, specific_room_keys=[group_room_key])
                    

    def groups_rename(self, group):
        """
        Update default channels for group or project
        :param group:
        :return: True if successful, False if there were any errors
        """
        # Rename configured channels
        success = True
        for room_key, room_name_code in settings.COSINNUS_ROCKET_GROUP_ROOM_NAMES_MAP.items():
            room_id = self.get_group_id(group, room_key=room_key)
            if room_id:
                room_name = room_name_code % group.slug
                response = self.rocket.groups_rename(room_id=room_id, name=room_name).json()
                if not response.get('success'):
                    logger.error('RocketChat: groups_rename ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
                    success = False
        return success
    
    def group_set_topic_to_url(self, group, specific_room_keys=None):
        """ Sets the CosinnusGroup url as topic of the group's room 
            @param specific_room_keysspecific_room_keys: if set to a list, the topic will only be 
                set for those specific room names, instead of for all rooms of that group """
        room_keys = specific_room_keys or settings.COSINNUS_ROCKET_GROUP_ROOM_KEYS
        for group_room_key in room_keys:
            # check if group room exists
            room_id = group.settings.get(f'{PROFILE_SETTING_ROCKET_CHAT_ID}_{group_room_key}', None)
            if room_id:
                response = self.rocket.groups_set_topic(room_id=room_id, topic=group.get_absolute_url()).json()
                if not response.get('success'):
                    logger.error('RocketChat: groups_set_topic: ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
        
    def groups_archive(self, group, specific_room_keys=None, specific_room_ids=None):
        """
        Archive channels for group or project
        :param group:
        :return: True if successful, False if there were any errors
        """
        # Archive given rooms
        success = True
        room_keys = specific_room_keys or settings.COSINNUS_ROCKET_GROUP_ROOM_KEYS
        room_ids = specific_room_ids or [self.get_group_id(group, room_key=room_key) for room_key in room_keys]
        for room_id in room_ids:
            if room_id:
                response = self.rocket.groups_archive(room_id=room_id).json()
                if not response.get('success'):
                    logger.error('RocketChat: groups_archive ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
                    success = False
        return success
    
    def groups_unarchive(self, group, specific_room_keys=None, specific_room_ids=None):
        """
        Unarchive channels for group or project
        :param group:
        :return: True if successful, False if there were any errors
        """
        # Unarchive given rooms
        success = True
        room_keys = specific_room_keys or settings.COSINNUS_ROCKET_GROUP_ROOM_KEYS
        room_ids = specific_room_ids or [self.get_group_id(group, room_key=room_key) for room_key in room_keys]
        for room_id in room_ids:
            if room_id:
                response = self.rocket.groups_unarchive(room_id=room_id).json()
                if not response.get('success'):
                    logger.error('RocketChat: groups_unarchive ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
                    success = False
        return success

    def groups_delete(self, group):
        """
        Delete default channels for group or project
        :param group:
        :return: True if successful, False if there were any errors
        """
        # Delete configured channels
        success = True
        for room in settings.COSINNUS_ROCKET_GROUP_ROOM_KEYS:
            room_id = self.get_group_id(group, room_key=room)
            if room_id:
                response = self.rocket.groups_delete(room_id=room_id).json()
                if not response.get('success'):
                    logger.error('RocketChat: groups_delete ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
                    success = False
        return success

    def invite_or_kick_for_membership(self, membership):
        """ For a CosinnusGroupMembership, force do:
                either kick or invite and promote or demote a user depending on their status """
        is_pending = membership.status in (MEMBERSHIP_PENDING, MEMBERSHIP_INVITED_PENDING)
        if is_pending:
            self.groups_kick(membership)
        else:
            self.groups_invite(membership)
            if membership.status == MEMBERSHIP_ADMIN:
                self.groups_add_moderator(membership)
            else:
                self.groups_remove_moderator(membership)
    
    def groups_invite(self, membership):
        """
        Create membership for default channels
        :param group:
        :return:
        """
        user_id = self.get_user_id(membership.user)
        if not user_id:
            return
        
        # Create role in general and news group
        for room in settings.COSINNUS_ROCKET_GROUP_ROOM_KEYS:
            room_id = self.get_group_id(membership.group, room_key=room)
            if room_id:
                response = self.rocket.groups_invite(room_id=room_id, user_id=user_id).json()
                if not response.get('success'):
                    logger.error('RocketChat: groups_invite ' + response.get('errorType', '<No Error Type>'), extra={'response': response})

    def groups_kick(self, membership):
        """
        Delete membership for default channels
        :param group:
        :return:
        """
        user_id = self.get_user_id(membership.user)
        if not user_id:
            return
        
        # Remove role in general and news group
        for room in settings.COSINNUS_ROCKET_GROUP_ROOM_KEYS:
            room_id = self.get_group_id(membership.group, room_key=room)
            if room_id:
                response = self.rocket.groups_kick(room_id=room_id, user_id=user_id).json()
                if not response.get('success'):
                    logger.error('RocketChat: groups_kick ' + response.get('errorType', '<No Error Type>'), extra={'response': response})

    def groups_add_moderator(self, membership):
        """
        Add role to user in group
        :param group:
        :return:
        """
        user_id = self.get_user_id(membership.user)
        if not user_id:
            return
        
        # Add moderator in general and news group
        for room in settings.COSINNUS_ROCKET_GROUP_ROOM_KEYS:
            room_id = self.get_group_id(membership.group, room_key=room)
            if room_id:
                response = self.rocket.groups_add_moderator(room_id=room_id, user_id=user_id).json()
                if not response.get('success') and not response.get('errorType', '') == 'error-user-already-moderator':
                    logger.error('RocketChat: groups_add_moderator ' + response.get('errorType', '<No Error Type>'), extra={'response': response})

    def groups_remove_moderator(self, membership):
        """
        Remove role from user in group
        :param group:
        :return:
        """
        user_id = self.get_user_id(membership.user)
        if not user_id:
            return
        
        # Remove moderator in general and news group
        for room in settings.COSINNUS_ROCKET_GROUP_ROOM_KEYS:
            room_id = self.get_group_id(membership.group, room_key=room)
            if room_id:
                response = self.rocket.groups_remove_moderator(room_id=room_id, user_id=user_id).json()
                if not response.get('success') and not response.get('errorType', '') == 'error-user-not-moderator':
                    logger.error('RocketChat: groups_remove_moderator ' + response.get('errorType', '<No Error Type>'), extra={'response': response})

    def add_member_to_room(self, user, room_id):
        """ Add a member to a given room """
        user_id = self.get_user_id(user)
        if not user_id:
            return
        response = self.rocket.groups_invite(room_id=room_id, user_id=user_id).json()
        if not response.get('success'):
            logger.error('RocketChat: Direct room_add_member: ' + response.get('errorType', '<No Error Type>'), extra={'user_email': user.email, 'response': response})

    def remove_member_from_room(self, user, room_id):
        """ Remove a member for a given room """
        user_id = self.get_user_id(user)
        if not user_id:
            return
        response = self.rocket.groups_kick(room_id=room_id, user_id=user_id).json()
        if not response.get('success'):
            logger.error('RocketChat: Direct room_remove_member: ' + response.get('errorType', '<No Error Type>'), extra={'user_email': user.email, 'response': response})

    def add_moderator_to_room(self, user, room_id):
        """ Add a moderator to a given room """
        user_id = self.get_user_id(user)
        if not user_id:
            return
        response = self.rocket.groups_add_moderator(room_id=room_id, user_id=user_id).json()
        if not response.get('success'):
            logger.error('RocketChat: Direct room_remove_moderator: ' + response.get('errorType', '<No Error Type>'), extra={'user_email': user.email, 'response': response})

    def remove_moderator_from_room(self, user, room_id):
        """ Remove a moderator for a given room """
        user_id = self.get_user_id(user)
        if not user_id:
            return
        response = self.rocket.groups_remove_moderator(room_id=room_id, user_id=user_id).json()
        if not response.get('success'):
            logger.error('RocketChat: Direct groups_remove_moderator: ' + response.get('errorType', '<No Error Type>'), extra={'user_email': user.email, 'response': response})

    def format_message(self, text):
        """
        Replace WECHANGE formatting language with Rocket.Chat formatting language:
        Rocket.Chat:
            Bold: *Lorem ipsum dolor* ;
            Italic: _Lorem ipsum dolor_ ;
            Strike: ~Lorem ipsum dolor~ ;
            Inline code: `Lorem ipsum dolor`;
            Image: ![Alt text](https://rocket.chat/favicon.ico) ;
            Link: [Lorem ipsum dolor](https://www.rocket.chat/) or <https://www.rocket.chat/ |Lorem ipsum dolor> ;
        :param text:
        :return:
        """
        # Unordered lists: _ to - / * to -
        text = re.sub(r'\n_ ', '\n- ', text)
        text = re.sub(r'\n\* ', '\n- ', text)
        # Italic: * to _
        text = re.sub(r'(^|\n|[^\*])\*($|\n|[^\*])', r'\1_\2', text)
        # Bold: ** to *
        text = re.sub(r'\*\*', '*', text)
        # Strike: ~~ to ~
        text = re.sub(r'~~', '~', text)
        return text
    
    def _format_note_message(self, note):
        """ Formats a Note to a readable chat message """
        url = note.get_absolute_url()
        text = self.format_message(note.text)
        if settings.COSINNUS_ROCKET_NOTE_POST_RELAY_TRUNCATE_WORD_COUNT:
            text = truncatewords(text, settings.COSINNUS_ROCKET_NOTE_POST_RELAY_TRUNCATE_WORD_COUNT)
        author_name = full_name(note.creator)
        note_title = note.title if not note.title == note.EMPTY_TITLE_PLACEHOLDER else ''
        title = f'{settings.COSINNUS_ROCKET_NEWS_BOT_EMOTE} *{author_name}: {note_title}*\n' 
        message = f'{title}{text}\n[{url}]({url})'
        return message
    
    def notes_create(self, note):
        """
        Create message for new note in default channel of group/project
        :param group:
        :return:
        """
        room_key = settings.COSINNUS_ROCKET_NOTE_POST_RELAY_ROOM_KEY
        if not room_key:
            return
        room_id = self.get_group_id(note.group, room_key=room_key)
        if not room_id:
            return
        message = self._format_note_message(note)
        response = self.rocket.chat_post_message(text=message, room_id=room_id).json()
        if not response.get('success'):
            logger.error('RocketChat: notes_create did not return a success response', extra={'response': response})
        msg_id = response.get('message', {}).get('_id')

        # Save Rocket.Chat message ID to note instance
        note.settings[ROCKETCHAT_NOTE_ID_SETTINGS_KEY] = msg_id
        # Update note settings without triggering signals to prevent cycles
        type(note).objects.filter(pk=note.pk).update(settings=note.settings)

    def notes_update(self, note):
        """
        Update message for note in default channel of group/project
        :param group:
        :return:
        """
        room_key = settings.COSINNUS_ROCKET_NOTE_POST_RELAY_ROOM_KEY
        if not room_key:
            return
        room_id = self.get_group_id(note.group, room_key=room_key)
        msg_id = note.settings.get(ROCKETCHAT_NOTE_ID_SETTINGS_KEY, None)
        if not msg_id or not room_id:
            return
        message = self._format_note_message(note)
        response = self.rocket.chat_update(msg_id=msg_id, room_id=room_id, text=message).json()
        if not response.get('success'):
            if response.get('error', None) == 'The room id provided does not match where the message is from.':
                # if the room has moved, we cannot reach the note anymore, ignore this error
                return
            logger.error('RocketChat: notes_update did not return a success response', extra={'response': response})

    def notes_attachments_update(self, note):
        """
        ** Currently disabled **
        Update attachments for note in default channel of group/project
        Unfortunately we cannot delete/update existing uploads, sincee rooms_upload doesn't return the message ID yet
        :param group:
        :return:
        """
        room_key = settings.COSINNUS_ROCKET_NOTE_POST_RELAY_ROOM_KEY
        if not room_key:
            return
        room_id = self.get_group_id(note.group, room_key=room_key)
        msg_id = note.settings.get(ROCKETCHAT_NOTE_ID_SETTINGS_KEY)
        if not msg_id or not room_id:
            return

        # Delete existing attachments
        # for att_id in note.settings.get('rocket_chat_attachment_ids', []):
        #     response = self.rocket.chat_delete(room_id=room_id, msg_id=att_id).json()
        #     if not response.get('success'):
        #         logger.error('RocketChat: notes_attachments_update', extra={'response': response})

        # Upload attachments
        # attachment_ids = []
        for att in note.attached_objects.all():
            att_file = att.target_object
            response = self.rocket.rooms_upload(rid=room_id,
                                                file=att_file.file.path,
                                                filename=att_file._sourcefilename,
                                                mimetype=att_file.mimetype,
                                                tmid=msg_id).json()
            if not response.get('success'):
                logger.error('RocketChat: notes_attachments_update did not return a success response', extra={'response': response})
            # attachment_ids.append(response.get('message', {}).get('_id'))

        # note.settings['rocket_chat_attachment_ids'] = attachment_ids
        # Update note settings without triggering signals to prevent cycles
        # type(note).objects.filter(pk=note.pk).update(settings=note.settings)

    def notes_delete(self, note):
        """
        Delete message for note in default channel of group/project
        :param group:
        :return:
        """
        room_key = settings.COSINNUS_ROCKET_NOTE_POST_RELAY_ROOM_KEY
        if not room_key:
            return
        msg_id = note.settings.get(ROCKETCHAT_NOTE_ID_SETTINGS_KEY)
        room_id = self.get_group_id(note.group, room_key=room_key)
        if not msg_id or not room_id:
            return
        response = self.rocket.chat_delete(room_id=room_id, msg_id=msg_id).json()
        if not response.get('success'):
            if response.get('error', None) == 'The room id provided does not match where the message is from.':
                # if the room has moved, we cannot reach the note anymore, ignore this error
                return
            logger.error('RocketChat: notes_delete did not return a success response', extra={'response': response})

    def unread_messages(self, user):
        """
        Get number of unread messages for user
        :param user:
        :return:
        """
        if not hasattr(user, 'cosinnus_profile'):
            return
        profile = user.cosinnus_profile

        try:
            user_connection = self._get_user_connection(user)
            if not user_connection:
                return 0
            response = user_connection.subscriptions_get()

            # if we didn't receive a successful response, the server may be down or the user logged out
            # reset the user connection and let the response be tried on the next run
            if not response.status_code == 200:
                delete_cached_rocket_connection(rocket_username=profile.rocket_username)
                logger.warn('RocketChat: Rocket: unread_message_count: non-200 response.',
                            extra={'response': response, 'status': response.status_code, 'content': response.content})
                return 0

            # check if we got proper data back from the API
            response_json = response.json()
            if not response_json.get('success'):
                logger.error('RocketChat: subscriptions_get did not return a success', response_json)
                return 0

            # add all unread channel updates and return
            return sum(subscription['unread'] for subscription in response_json['update'])

        except RocketConnectionException as e:
            logger.warn('RocketChat: unread message count: connection exception',
                     extra={'exception': e})
        except Exception as e:
            logger.error('RocketChat: unread message count: unexpected exception',
                     extra={'exception': e})
            logger.exception(e)
    
    def get_user_preferences(self, user):
        """ Gets the given user's rocketchat preferences.
            Note: the preference set is empty for preferences that have never been changed
                from the default!
            @return: a dict of preferences. `None`, if there was an error.
        """
        user_connection = self._get_user_connection(user)
        if not user_connection:
            return None
        
        response = user_connection.users_get_preferences().json()
        if not response.get('success') or not 'preferences' in response:
            # if the preferences aren't set up yet, don't count this ans an error
            if response.get('error', None) != "FAILED TO RETRIEVE USER PREFERENCES BECAUSE THEY HAVEN'T BEEN SET UP BY THE USER YET":
                logger.error('RocketChat: get_user_preferences did not receive a success response or data: ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
            return None
        return response.get('preferences', None)
        
    def get_user_email_preference(self, user):
        """ Gets the user preference for email notifications
            Preference for emails is: 'emailNotificationMode': 'mentions'|'default'|'nothing'
            @return: one of the values of `ROCKETCHAT_PREFERENCES_EMAIL_NOTIFICATION` or None if 
                no setting is set, it is of unknown value or an error occured """
        prefs = self.get_user_preferences(user)
        if not prefs:
            return None
        email_pref = prefs.get('emailNotificationMode', None)
        if email_pref and email_pref not in ROCKETCHAT_PREFERENCES_EMAIL_NOTIFICATION:
            logger.error('RocketChat: get_user_email_preference did not receive a known value: ' + str(email_pref))
            return None
        return email_pref
    
    def set_user_email_preference(self, user, preference):
        """ Sets the user's email preferences to be one of the values of `ROCKETCHAT_PREFERENCES_EMAIL_NOTIFICATION`
            @return: True if successful, False if not """
        if not preference in ROCKETCHAT_PREFERENCES_EMAIL_NOTIFICATION:
            logger.error('RocketChat: set_user_email_preference got an invalid value: ' + str(preference))
            return False
        user_connection = self._get_user_connection(user)
        if not user_connection:
            return False
        user_id = user.cosinnus_profile.settings.get(PROFILE_SETTING_ROCKET_CHAT_ID, None)
        if not user_id:
            # user not connected to rocketchat
            return False
        data = {
            'emailNotificationMode': preference,
        }
        response = user_connection.users_set_preferences(user_id, data).json()
        if not response.get('success'):
            logger.error('RocketChat: set_user_email_preference did not receive a success response: ' + response.get('errorType', '<No Error Type>'), extra={'response': response})
            return False
        return True
        
    def _get_user_connection(self, user):
        """ Returns a user-specific rocketchat connection for the given user, 
            or None if this fails for any reason """
            
        profile = user.cosinnus_profile
        user_connection = None
        try:
            user_connection = get_cached_rocket_connection(rocket_username=profile.rocket_username, password=user.password,
                                         server_url=settings.COSINNUS_CHAT_BASE_URL)
        except RocketAuthenticationException:
            user_id = user.cosinnus_profile.settings.get(PROFILE_SETTING_ROCKET_CHAT_ID)
            if not user_id:
                # user not connected to rocketchat
                return None
            # try to re-initi the user's account and reconnect
            response = self.rocket.users_update(user_id=user_id, password=user.password).json()
            if not response.get('success'):
                logger.error('RocketChat: unread_messages did not receive a success response: ' + str(response.get('errorType', '<No Error Type>')), extra={'response': response})
                return None
            user_connection = get_cached_rocket_connection(rocket_username=profile.rocket_username, password=user.password,
                                         server_url=settings.COSINNUS_CHAT_BASE_URL, reset=True) # resets cache
        return user_connection
        
        
        