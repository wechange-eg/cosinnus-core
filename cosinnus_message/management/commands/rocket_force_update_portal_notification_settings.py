import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from cosinnus.conf import settings
from cosinnus.models.profile import PROFILE_SETTING_ROCKET_CHAT_USERNAME, GlobalUserNotificationSetting
from cosinnus.utils.permissions import check_user_can_receive_emails
from cosinnus.utils.user import filter_portal_users
from cosinnus_message.utils.utils import save_rocketchat_mail_notification_preference_for_user_setting

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):
    """
    Force sync the users RocketChat notification settings stored in the portal.
    """

    def handle(self, *args, **options):
        # confirm overwriting notifications settings stored in RocketChat
        message = (
            '\nThis will overwrite existing user notification settings in the RocketChat profiles!\n'
            'Are you sure you want to do this?\n\n'
            'Type "yes" to continue, or "no" to cancel: '
        )
        if input(message) != 'yes':
            raise CommandError('Notification settings sync canceled.')

        users = get_user_model().objects.all().filter(is_active=True)  # active users only
        users = filter_portal_users(users)  # from this portal
        users = users.exclude(email__startswith='__unverified__')
        users = users.exclude(password__exact='').exclude(password=None)  # with a password
        # note, we do include users with a real mail, but unverified flag, as their setting will be relevant once they
        # verify

        count = 0
        errors = 0
        total = len(users)
        for user in users:
            if not user.cosinnus_profile.settings.get(PROFILE_SETTING_ROCKET_CHAT_USERNAME, None):
                # ignore users without a RocketChat account
                self.stdout.write(
                    f'User {count + 1}/{total} ({errors} Errors): Skipping (user has no rocket account yet)'
                )
                count += 1
                continue

            try:
                if not check_user_can_receive_emails(user):
                    # if user cant receive emails, disable RocketChat notifications
                    rocket_user_notification_setting = GlobalUserNotificationSetting.ROCKETCHAT_SETTING_OFF
                else:
                    # user can receive emails
                    portal_user_notification_setting = GlobalUserNotificationSetting.objects.filter(user=user).first()
                    if portal_user_notification_setting:
                        # if the user has global notification settings, use the rocketchat_setting
                        rocket_user_notification_setting = portal_user_notification_setting.rocketchat_setting
                    else:
                        # otherwise use the default RocketChat notification setting
                        rocket_user_notification_setting = settings.COSINNUS_DEFAULT_ROCKETCHAT_NOTIFICATION_SETTING
                save_rocketchat_mail_notification_preference_for_user_setting(user, rocket_user_notification_setting)
                self.stdout.write(
                    f'User {count + 1}/{total} ({errors} Errors): Applied setting {rocket_user_notification_setting}'
                )
            except Exception as e:
                errors += 1
                self.stdout.write(f'User {count + 1}/{total} ({errors} Errors): Error! {str(e)}')
            count += 1
