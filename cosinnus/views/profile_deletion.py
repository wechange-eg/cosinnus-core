import logging
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils.crypto import get_random_string
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from oauth2_provider import models as oauth2_provider_models

from cosinnus.core import signals
from cosinnus.core.mail import send_html_mail
from cosinnus.models.group import CosinnusGroup, CosinnusGroupMembership
from cosinnus.models.membership import MEMBERSHIP_ADMIN, MEMBERSHIP_MANAGER, MEMBERSHIP_MEMBER
from cosinnus.models.profile import get_user_profile_model
from cosinnus.models.tagged import get_tag_object_model
from cosinnus.models.widget import WidgetConfig
from cosinnus.templatetags.cosinnus_tags import textfield
from cosinnus.views.group import mark_group_for_deletion

logger = logging.getLogger('cosinnus')


def deactivate_user(user):
    """Deactivates a user account"""
    user.is_active = False
    user.save()
    # save the user's profile as well,
    # as numerous triggers occur on the profile instead of the user object
    if hasattr(user, 'cosinnus_profile') and user.cosinnus_profile:
        user.cosinnus_profile.save()


def deactivate_user_and_mark_for_deletion(user, triggered_by_self=False, inactivity_deletion=False):
    """Deacitvates a user account and marks them for deletion in 30 days"""
    if triggered_by_self:
        # send a notification email ignoring notification settings for a user triggered deletion
        text = _(
            'Your platform profile stored with us under this email has been deactivated by you and was approved for '
            'deletion. The profile has been removed from the website and we will delete the account completely in 30 '
            'days.\n\nIf this has happened without your knowledge or if you change your mind in the meantime, please '
            'contact the portal administrators or the email address given in our imprint. Please note that the '
            'response time by e-mail may take longer in some cases. Please contact us as soon as possible if you would '
            'like to keep your profile.'
        )
        body_text = textfield(text)
        send_html_mail(user, _('Information about the deletion of your user account'), body_text, threaded=False)
    elif inactivity_deletion:
        # send notification for automatic deletion due to inactivity
        subject = _('Attention: Your profile has been deactivated will be deleted due to inactivity')
        text = _(
            'Your platform profile stored under this email has been deactivated by us and released for deletion. We '
            'will delete this account completely in 30 days.\n\nIf you change your mind  in the meantime, please '
            'contact the portal administrators or the email address given in our imprint. Please note that the '
            'response time by e-mail may take longer in some cases. Please contact us as soon as possible if you would '
            'like to keep your profile.'
        )
        body_text = textfield(text)
        # When errors occur when sending the notification for inactivity deletions do not deactivate the user.
        try:
            send_html_mail(user, subject, body_text, threaded=False, raise_on_error=True)
        except Exception as e:
            logger.warn(
                'Could not deactivate inactive user because of an exception while sending the notification email.',
                extra={'exception': e},
            )
            return

    if hasattr(user, 'cosinnus_profile') and user.cosinnus_profile:
        # add a marked-for-deletion flag and a cronjob, deleting the profile using this
        deletion_schedule_time = now() + timedelta(days=settings.COSINNUS_USER_PROFILE_DELETION_SCHEDULE_DAYS)
        user.cosinnus_profile.scheduled_for_deletion_at = deletion_schedule_time
        user.cosinnus_profile.deletion_triggered_by_self = triggered_by_self
        user.cosinnus_profile.save()
    deactivate_user(user)

    # send extended deactivation signal
    if hasattr(user, 'cosinnus_profile') and user.cosinnus_profile:
        signals.user_deactivated_and_marked_for_deletion.send(sender=None, profile=user.cosinnus_profile)


def reassign_admins_for_groups_of_deleted_user(user):
    """Reassigned group members to admins if the only group admin is automatically deleted."""
    for group in CosinnusGroup.objects.get_for_user(user):
        admins = CosinnusGroupMembership.objects.get_admins(group=group)
        members = CosinnusGroupMembership.objects.get_members(group=group)
        if [user.pk] == admins:
            # user is the only admin of the group
            other_members = set(members).difference(admins)
            if other_members:
                # make other members admins
                non_admin_status = [MEMBERSHIP_MANAGER, MEMBERSHIP_MEMBER]
                for membership in CosinnusGroupMembership.objects.filter(group=group, status__in=non_admin_status):
                    membership.status = MEMBERSHIP_ADMIN
                    membership.save()
            else:
                # user is the only member of the group
                mark_group_for_deletion(group, triggered_by_user=user)


def delete_guest_user(user, deactivate_only=True):
    """Deletes a user account (permanently or deactivate only) if they are a guest user.
    Used when a guest user account is no longer needed (after logout) or when it has become
    invalid (when the token or group it belongs to have been deleted).

    @param deactivate_only: if True, the guest account will only be disabled, which will still lead to
        the session becoming unusable. if False, the account will be irrevocably deleted."""
    if user.is_guest:
        if deactivate_only:
            user.is_active = False
            user.save()
        else:
            user.delete()


def reactivate_user(user):
    """Reactivates a user account and deletes their marked-for-deletion-flag"""
    user.is_active = True
    user.save()
    # save the user's profile as well,
    # as numerous triggers occur on the profile instead of the user object
    if hasattr(user, 'cosinnus_profile') and user.cosinnus_profile:
        # delete the marked-for-deletion flag
        user.cosinnus_profile.scheduled_for_deletion_at = None
        user.cosinnus_profile.deletion_triggered_by_self = False
        user.cosinnus_profile.save()
    else:
        # create a new userprofile if the old one was already deleted,
        # so we have a functioning user account again
        get_user_profile_model()._default_manager.get_for_user(user)


def delete_userprofile(user):
    """Deactivate and completely anonymize a user's profile, name and email,
    leaving only the empty User object.
    All content created by the user and foreign-key relations are preserved,
    but will display ""Deleted User)" as creator.
    Will not work on userprofiles whose user account is still active!"""

    if user.is_active:
        logger.warning(
            'Aborting user profile deletion because the user account was still active!', extra={'user_id': user.id}
        )
        return

    profile = user.cosinnus_profile if hasattr(user, 'cosinnus_profile') and user.cosinnus_profile else None

    # send deletion signal
    if profile:
        signals.pre_userprofile_delete.send(sender=None, profile=profile)

    # delete user widgets
    widgets = WidgetConfig.objects.filter(user_id__exact=user.pk)
    for widget in widgets:
        widget.delete()

    # leave all groups
    for membership in CosinnusGroupMembership.objects.filter(user=user):
        membership.delete()

    # delete user media_tag
    try:
        if profile and profile.media_tag:
            profile.media_tag.delete()
    except get_tag_object_model().DoesNotExist:
        pass

    # delete AllAuth user data
    if settings.COSINNUS_IS_OAUTH_CLIENT:
        from allauth.account.models import EmailAddress
        from allauth.socialaccount.models import SocialAccount

        SocialAccount.objects.filter(user=user).delete()
        EmailAddress.objects.filter(user=user).delete()

    # delete oauth2_provider user tokens and grants
    try:
        oauth2_provider_models.get_grant_model().objects.filter(user=user).delete()
        oauth2_provider_models.get_access_token_model().objects.filter(user=user).delete()
        oauth2_provider_models.get_refresh_token_model().objects.filter(user=user).delete()
    except Exception as e:
        logger.warn(
            "Userprofile delete: could not delete a user's oauth tokens because of an exception.",
            extra={'exception': e},
        )

    # delete user profile
    if profile:
        if profile.avatar:
            profile.avatar.delete(False)
        profile.delete()

    # set user to inactive and anonymize all data.
    user.first_name = 'deleted'
    user.last_name = 'user'
    user.username = user.id
    # replace e-mail with random address
    user.email = '__deleted_user__%s@deleted.com' % get_random_string(length=12)

    # we no longer retain a padded version of the user's email
    # scramble_cutoff = user._meta.get_field('email').max_length - len(scrambled_email_prefix) - 2
    # scrambled_email_prefix = scrambled_email_prefix[:scramble_cutoff]

    user.is_active = False
    user.save()


def send_user_inactivity_deactivation_notifications():
    """Sends notifications before automatic user deactivation due inactivity."""
    users_notified_count = 0
    users = get_user_model().objects.filter(is_active=True)
    for days_before_deactivation, time_message in settings.COSINNUS_INACTIVE_NOTIFICATIONS_BEFORE_DEACTIVATION.items():
        # get users that are notified according to the configured interval
        days_after_last_activity = settings.COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE - days_before_deactivation
        user_last_activity_date = (now() - timedelta(days=days_after_last_activity)).date()
        inactive_users = users.filter(
            Q(last_login__date=user_last_activity_date) | Q(last_login=None, date_joined__date=user_last_activity_date)
        )
        today = now().date()
        notify_users = inactive_users.filter(
            Q(cosinnus_profile__inactivity_notification_sent_at=None)
            | Q(cosinnus_profile__inactivity_notification_sent_at__date__lt=today)
        )

        for user in notify_users:
            # send notification email
            mail_subject = _('Your account will be deleted due to inactivity')
            mail_content = _(
                'Your entire account, profile and personal information will be deactivated and irrevocably deleted in '
                '%(deactivation_in)s.\n'
                'Your pads, news, uploaded files and other content will remain on the website. However, your name will '
                'no longer be displayed and your profile will no longer be linked to the content. On Rocket Chat, your '
                'profile direct messages will be deleted, but content within discussions and channels will remain. If '
                'you still want to delete content from yourself, you can do this now by deleting the content on the '
                'relevant pages.\n'
                'Your profile will first be deactivated and completely removed from the platform. After deactivation, '
                'it will be deleted from our database after %(deleted_after_days)s days and only then permanently.\n'
                'The account may be stored in our backup systems for up to 6 months after deletion. If this is too '
                'long for you, please contact the support team of this platform for immediate deletion.\n'
                'During this %(deleted_after_days)s-day period after deletion, the e-mail address of your account is '
                'reserved and cannot be used to register a new account.'
            ) % {
                'deleted_after_days': settings.COSINNUS_USER_PROFILE_DELETION_SCHEDULE_DAYS,
                'deactivation_in': time_message,
            }
            html_content = textfield(mail_content)
            send_html_mail(user, mail_subject, html_content)

            # update the notification send timestamp
            if hasattr(user, 'cosinnus_profile') and user.cosinnus_profile:
                user.cosinnus_profile.inactivity_notification_sent_at = now()
                user.cosinnus_profile.save()
            users_notified_count += 1

    return users_notified_count
