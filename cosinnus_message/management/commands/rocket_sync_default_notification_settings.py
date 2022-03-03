import logging

from django.core.management.base import BaseCommand

from cosinnus_message.rocket_chat import RocketChatConnection
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.models.group import CosinnusPortal
from cosinnus.utils.user import filter_portal_users
from cosinnus.conf import settings
from django.contrib.auth import get_user_model
from cosinnus_message.utils.utils import save_rocketchat_mail_notification_preference_for_user_setting
from cosinnus.utils.permissions import check_user_can_receive_emails
from cosinnus.models.profile import GlobalUserNotificationSetting,\
    PROFILE_SETTING_ROCKET_CHAT_USERNAME


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):
    """
    For all users who have *not yet* set any rocketchat mail notification preference, 
    this will set the equivalent of their current portal-mail notification setting 
    as their rocketchat-mail notification preference.
    Users who have saved their preference before are left untouched.
    
    This is not neccessary to run on new portals, as the setting is set on user creation already.
    """
    
    def add_arguments(self, parser):
        parser.add_argument('-u', '--use-user-setting', action='store_true', help='Infer the rocket setting from the the user notification instead of using the portal default setting')
    
    def handle(self, *args, **options):
        if not settings.COSINNUS_CHAT_USER:
            return
        use_user_setting = options['use_user_setting']
        default_setting = settings.COSINNUS_DEFAULT_ROCKETCHAT_NOTIFICATION_SETTING
        
        rocket = RocketChatConnection(stdout=self.stdout, stderr=self.stderr)
        users = get_user_model().objects.all().filter(is_active=True) # active users only
        users = filter_portal_users(users) # from this portal 
        users = users.exclude(email__startswith='__unverified__')
        users = users.exclude(password__exact='').exclude(password=None) # with a password
        # note, we do include users with a real mail, but unverified flag, as their setting will be relevant once they verify
        count = 0
        errors = 0
        total = len(users)
        for user in users:
            if not user.cosinnus_profile.settings.get(PROFILE_SETTING_ROCKET_CHAT_USERNAME, None):
                self.stdout.write(f'User {count+1}/{total} ({errors} Errors): Skipping (user has no rocket account yet)')
                count += 1
                continue
            
            try:
                pref = rocket.get_user_email_preference(user)
                # if the user hasn't got a definite value set in their profile, we set the portal's default
                if not pref:
                    if use_user_setting:
                        # apply the inferred user notification settings
                        if check_user_can_receive_emails(user):
                            user_setting = GlobalUserNotificationSetting.ROCKETCHAT_SETTING_MENTIONS
                        else:
                            user_setting = GlobalUserNotificationSetting.ROCKETCHAT_SETTING_OFF
                        target_setting = user_setting
                    else:
                        # apply the default portal settings for unset users instead!
                        target_setting = default_setting 
                    save_rocketchat_mail_notification_preference_for_user_setting(
                        user,
                        target_setting
                    )
                    self.stdout.write(f'User {count+1}/{total} ({errors} Errors): Applied setting {target_setting}')
                else:
                    self.stdout.write(f'User {count+1}/{total} ({errors} Errors): Skipping (they had setting "{pref}")')
            except Exception as e:
                errors += 1
                self.stdout.write(f'User {count+1}/{total} ({errors} Errors): Error! {str(e)}')
            count += 1
