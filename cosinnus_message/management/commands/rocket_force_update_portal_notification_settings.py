import logging

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.profile import PROFILE_SETTING_ROCKET_CHAT_USERNAME, GlobalUserNotificationSetting
from cosinnus.utils.permissions import check_user_can_receive_emails
from cosinnus.utils.user import filter_active_users, filter_portal_users
from cosinnus_message.utils.utils import save_rocketchat_mail_notification_preference_for_user_setting

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):
    """
    Force sync the users RocketChat notification settings stored in the portal.
    Can be safely called multiple times.
    """

    help = (
        'Force sync the users RocketChat notification settings stored in the portal. '
        'Can be safely called multiple times.'
    )

    def handle(self, *args, **options):
        # confirm overwriting notifications settings stored in RocketChat
        message = (
            '\nThis will overwrite existing user notification settings in the RocketChat profiles!\n'
            'Are you sure you want to do this?\n\n'
            'Type "yes" to continue, or "no" to cancel: '
        )
        if input(message) != 'yes':
            raise CommandError('Notification settings sync canceled.')

        # get active portal users with verified email
        # Note: we exclude users with unverified emails, as with check_user_can_receive_emails we would falsely disable
        # their RocketChat notification, not considering the actual setting.
        users = get_user_model().objects.all()
        users = users.prefetch_related('cosinnus_profile')
        users = filter_portal_users(users)
        users = filter_active_users(users)
        if CosinnusPortal.get_current().email_needs_verification:
            users = users.filter(cosinnus_profile__email_verified=True)

        count = 0
        errors = 0
        total = len(users)
        for user in users:
            if not hasattr(user, 'cosinnus_profile'):
                # ignore users without a cosinnus_profile
                self.stdout.write(f'User {count + 1}/{total} ({errors} Errors): Skipping (user has no profile)')
                count += 1
                continue
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
