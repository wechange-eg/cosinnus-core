from datetime import datetime, timedelta, timezone
from unittest.mock import ANY, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import translation
from django.utils.timezone import now
from freezegun import freeze_time
from rest_framework.test import override_settings

import cosinnus_notifications
from cosinnus.conf import settings
from cosinnus.cron import (
    DeleteScheduledGroups,
    DeleteScheduledUserProfiles,
    MarkInactiveGroupsForDeletion,
    MarkInactiveUsersForDeletion,
    SendGroupsInactivityNotifications,
    SendUserInactivityNotifications,
    UpdateGroupsLastActivity,
)
from cosinnus.models import MEMBERSHIP_PENDING
from cosinnus.models.group import MEMBERSHIP_ADMIN, MEMBERSHIP_MEMBER, CosinnusGroupMembership
from cosinnus.models.group_extra import CosinnusSociety
from cosinnus.utils.inactivity import format_inactivity_duration
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.views.group_deletion import get_groups_due_for_inactivity_deactivation, mark_group_for_deletion
from cosinnus.views.profile_deletion import (
    deactivate_user_and_mark_for_deletion,
    delete_userprofile,
    get_users_due_for_inactivity_deactivation,
)
from cosinnus_note.models import Note

# Patch threads as threads do not work with Django tests as they don't get the correct test database connection.
cosinnus_notifications.notifications.NotificationsThread.start = lambda self: self.run()


def create_active_test_user(username='user'):
    test_user_data = {'username': username, 'email': 'testuser@example.com', 'first_name': 'Test', 'last_name': 'User'}
    test_user = get_user_model().objects.create(**test_user_data)
    test_user.last_login = now()
    test_user.save()
    test_user.cosinnus_profile.tos_accepted = True
    test_user.cosinnus_profile.email_verified = True
    test_user.cosinnus_profile.language = 'en'
    test_user.cosinnus_profile.save()
    return test_user


class InactivityNotificationCronTest(SimpleTestCase):
    def test_user_notification_failure_is_logged_as_critical(self):
        with patch(
            'cosinnus.cron.send_user_inactivity_deactivation_notifications',
            side_effect=RuntimeError('Mail delivery failed'),
        ), self.assertLogs('cosinnus', level='CRITICAL') as logs:
            result = SendUserInactivityNotifications().do()

        self.assertEqual(result, 'An error occurred during cron job execution.')
        self.assertIn('Sending user inactivity notifications failed.', logs.output[0])

    def test_group_notification_failure_is_logged_as_critical(self):
        with patch(
            'cosinnus.cron.send_group_inactivity_deactivation_notifications',
            side_effect=RuntimeError('Mail delivery failed'),
        ), self.assertLogs('cosinnus', level='CRITICAL') as logs:
            result = SendGroupsInactivityNotifications().do()

        self.assertEqual(result, 'An error occurred during cron job execution.')
        self.assertIn('Sending group inactivity notifications failed.', logs.output[0])


class TestUserMixin:
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_user = create_active_test_user()


class UserDeletionTest(TestUserMixin, TestCase):
    @override_settings(COSINNUS_USER_PROFILE_DELETION_SCHEDULE_DAYS=45)
    @freeze_time('2024-01-01')
    @patch('cosinnus.views.profile_deletion.send_html_mail')
    def test_self_deactivation_uses_configured_deletion_period(self, send_mail_mock):
        with translation.override('en'):
            deactivate_user_and_mark_for_deletion(self.test_user, triggered_by_self=True)

        send_mail_mock.assert_called_once()
        mail_body = send_mail_mock.call_args.args[2]
        self.assertIn('45 days', mail_body)
        self.assertEqual(self.test_user.cosinnus_profile.scheduled_for_deletion_at, now() + timedelta(days=45))

    @override_settings(COSINNUS_USER_PROFILE_DELETION_SCHEDULE_DAYS=45)
    @freeze_time('2024-01-01')
    @patch('cosinnus.views.profile_deletion.send_html_mail')
    def test_inactivity_deactivation_uses_configured_deletion_period(self, send_mail_mock):
        with translation.override('en'):
            deactivate_user_and_mark_for_deletion(self.test_user, inactivity_deletion=True)

        send_mail_mock.assert_called_once()
        mail_body = send_mail_mock.call_args.args[2]
        self.assertIn('45 days', mail_body)
        self.assertEqual(self.test_user.cosinnus_profile.scheduled_for_deletion_at, now() + timedelta(days=45))

    def test_user_fields(self):
        self.test_user.is_active = False
        self.test_user.save()
        delete_userprofile(self.test_user)

        self.test_user.refresh_from_db()
        self.assertFalse(self.test_user.is_active)
        self.assertEqual(self.test_user.first_name, 'deleted')
        self.assertEqual(self.test_user.last_name, 'user')
        self.assertIn('__deleted_user__', self.test_user.email)

    def test_user_delete_cron_job(self):
        self.test_user.cosinnus_profile.scheduled_for_deletion_at = datetime(2024, 2, 1)
        self.test_user.cosinnus_profile.save()

        # profile is not deleted before the scheduled time
        with freeze_time('2024-01-31'):
            DeleteScheduledUserProfiles().do()
            self.test_user.refresh_from_db()
            self.assertNotEqual(self.test_user.first_name, 'deleted')

        # active profiles are not deleted at scheduled time
        with freeze_time('2024-02-1'):
            DeleteScheduledUserProfiles().do()
            self.test_user.refresh_from_db()
            self.assertNotEqual(self.test_user.first_name, 'deleted')

        # inactive profiles are deleted at scheduled time
        self.test_user.is_active = False
        self.test_user.save()
        with freeze_time('2024-02-1'):
            DeleteScheduledUserProfiles().do()
            self.test_user.refresh_from_db()
            self.assertEqual(self.test_user.first_name, 'deleted')

    def test_reactivating_user_aborts_deletion(self):
        self.test_user.is_active = False
        self.test_user.save()
        self.test_user.cosinnus_profile.scheduled_for_deletion_at = now()
        self.test_user.is_active = True
        self.test_user.save()
        self.test_user.cosinnus_profile.refresh_from_db()
        self.assertIsNone(self.test_user.cosinnus_profile.scheduled_for_deletion_at)


class UserManualDeletionTest(TestUserMixin, TestCase):
    @freeze_time('2024-01-01')
    @patch('cosinnus.views.profile_deletion.send_html_mail')
    def test_user_delete_view_schedules_deletion(self, send_mail_mock):
        self.client.force_login(self.test_user)
        self.assertTrue(self.test_user.is_active)
        self.assertIsNone(self.test_user.cosinnus_profile.scheduled_for_deletion_at)

        # delete user
        user_delete_url = reverse('cosinnus:profile-delete')
        response = self.client.post(user_delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.get('location').startswith(reverse('login')))  # allow subpaths/GET-params in URL
        self.test_user.refresh_from_db()

        # check the user is deactivated and scheduled for deletion
        self.assertFalse(self.test_user.is_active)
        expected_deletion_at = now() + timedelta(days=settings.COSINNUS_USER_PROFILE_DELETION_SCHEDULE_DAYS)
        self.assertEqual(self.test_user.cosinnus_profile.scheduled_for_deletion_at, expected_deletion_at)

        # check that a notification email was send
        send_mail_mock.assert_called_once_with(
            self.test_user, 'Information about the deletion of your user account', ANY, threaded=False
        )
        send_mail_mock.reset_mock()


class UserInactivityDeletionTest(TestUserMixin, TestCase):
    @override_settings(
        COSINNUS_USER_INACTIVITY_SCHEDULE={
            'days': 10,
            'warnings': {
                3: {
                    'subject_template': 'cosinnus/mail/inactivity/user_subject.txt',
                    'body_template': 'cosinnus/mail/inactivity/user_body.txt',
                },
            },
        },
    )
    @patch('cosinnus.views.profile_deletion.send_html_mail')
    def test_overdue_user_is_deactivated_without_catch_up_warnings(self, send_mail_mock):
        self.test_user.last_login = datetime(2024, 1, 18, tzinfo=timezone.utc)
        self.test_user.save()

        with freeze_time('2024-02-01'):
            SendUserInactivityNotifications().do()
            send_mail_mock.assert_not_called()

            MarkInactiveUsersForDeletion().do()
            send_mail_mock.assert_called_once()

        self.test_user.refresh_from_db()
        self.assertFalse(self.test_user.is_active)

    @patch('cosinnus.views.profile_deletion.send_html_mail')
    def test_inactivity_notifications(self, send_mail_mock):
        last_login = datetime(2014, 1, 1)
        self.test_user.last_login = last_login
        self.test_user.save()

        schedule = settings.COSINNUS_USER_INACTIVITY_SCHEDULE
        deactivation_date = last_login + timedelta(days=schedule['days'])
        for days_before_deactivation, warning_config in schedule['warnings'].items():
            notification_date = deactivation_date - timedelta(days=days_before_deactivation)

            # no notification is sent the day before scheduled date
            day_before_notification = notification_date - timedelta(days=1)
            with freeze_time(day_before_notification):
                SendUserInactivityNotifications().do()
                self.assertFalse(send_mail_mock.called)

            # notification is sent at the scheduled date
            with freeze_time(notification_date):
                SendUserInactivityNotifications().do()
                send_mail_mock.assert_called_once_with(
                    self.test_user,
                    'Your account will be deleted due to inactivity',
                    ANY,
                    raise_on_error=True,
                )

                # make sure placeholders are filled in mail content
                warning_text = format_inactivity_duration(days_before_deactivation, warning_config, 'en')
                mail_body = send_mail_mock.call_args.args[2]
                self.assertIn(f'deactivated in {warning_text}', mail_body)
                send_mail_mock.reset_mock()

                # notification is not send again
                SendUserInactivityNotifications().do()
                self.assertFalse(send_mail_mock.called)

            # no notification is sent the day after scheduled date, if not enabled by settings
            if (days_before_deactivation - 1) not in settings.COSINNUS_USER_INACTIVITY_SCHEDULE['warnings']:
                day_after_notification = notification_date + timedelta(days=1)
                with freeze_time(day_after_notification):
                    SendUserInactivityNotifications().do()
                    self.assertFalse(send_mail_mock.called)

    @override_settings(COSINNUS_INACTIVITY_DRY_RUN=True)
    @patch('cosinnus.views.profile_deletion.send_html_mail')
    def test_inactivity_notification_dry_run(self, send_mail_mock):
        last_login = datetime(2014, 1, 1)
        schedule = settings.COSINNUS_USER_INACTIVITY_SCHEDULE
        warning_days_before_deactivation = next(iter(schedule['warnings']))
        warning_notification_date = last_login + timedelta(days=schedule['days'] - warning_days_before_deactivation)

        self.test_user.last_login = last_login
        self.test_user.save()

        with freeze_time(warning_notification_date):
            result = SendUserInactivityNotifications().do()

        self.assertEqual(result, '1 users would be notified (dry run).')
        send_mail_mock.assert_not_called()
        self.test_user.cosinnus_profile.refresh_from_db()
        self.assertIsNone(self.test_user.cosinnus_profile.inactivity_notification_sent_at)

    @patch('cosinnus.views.profile_deletion.send_html_mail')
    def test_scheduled_deletion(self, send_mail_mock):
        last_login = datetime(2014, 1, 1, tzinfo=timezone.utc)
        self.test_user.last_login = last_login
        self.test_user.save()

        deactivation_date = last_login + timedelta(days=settings.COSINNUS_USER_INACTIVITY_SCHEDULE['days'], seconds=1)

        # do not schedule before date
        day_before_deactivation = deactivation_date - timedelta(days=1)
        with freeze_time(day_before_deactivation):
            MarkInactiveUsersForDeletion().do()
            self.test_user.cosinnus_profile.refresh_from_db()
            self.assertIsNone(self.test_user.cosinnus_profile.scheduled_for_deletion_at)
            self.assertFalse(send_mail_mock.called)

        # deletion is scheduled after the schedule interval is passed
        expected_deletion = deactivation_date + timedelta(days=settings.COSINNUS_USER_PROFILE_DELETION_SCHEDULE_DAYS)
        with freeze_time(deactivation_date):
            MarkInactiveUsersForDeletion().do()
            self.test_user.cosinnus_profile.refresh_from_db()
            self.assertEqual(self.test_user.cosinnus_profile.scheduled_for_deletion_at, expected_deletion)
            send_mail_mock.assert_called_once_with(
                self.test_user,
                'Attention: Your profile has been deactivated and will be deleted due to inactivity',
                ANY,
                threaded=False,
                raise_on_error=True,
            )
            send_mail_mock.reset_mock()

        # do not reschedule already scheduled deletions
        day_after_deactivation = deactivation_date + timedelta(days=1)
        with freeze_time(day_after_deactivation):
            self.assertEqual(self.test_user.cosinnus_profile.scheduled_for_deletion_at, expected_deletion)
            MarkInactiveUsersForDeletion().do()
            self.test_user.cosinnus_profile.refresh_from_db()
            self.assertEqual(self.test_user.cosinnus_profile.scheduled_for_deletion_at, expected_deletion)

    @override_settings(COSINNUS_INACTIVITY_DRY_RUN=True)
    @patch('cosinnus.views.profile_deletion.send_html_mail')
    def test_inactivity_deactivation_dry_run(self, send_mail_mock):
        schedule = settings.COSINNUS_USER_INACTIVITY_SCHEDULE
        last_login = datetime(2014, 1, 1, tzinfo=timezone.utc)
        deactivation_date = last_login + timedelta(days=schedule['days'], seconds=1)

        self.test_user.last_login = last_login
        self.test_user.save()

        with freeze_time(deactivation_date):
            result = MarkInactiveUsersForDeletion().do()

        self.assertEqual(result, '1 users would be scheduled for deletion (dry run).')
        send_mail_mock.assert_not_called()
        self.test_user.refresh_from_db()
        self.assertTrue(self.test_user.is_active)
        self.assertIsNone(self.test_user.cosinnus_profile.scheduled_for_deletion_at)

    @patch('cosinnus.views.profile_deletion.send_html_mail', side_effect=Exception)
    def test_scheduled_deletion_email_exception(self, send_mail_mock):
        last_login = datetime(2014, 1, 1, tzinfo=timezone.utc)
        self.test_user.last_login = last_login
        self.test_user.save()

        deactivation_date = last_login + timedelta(days=settings.COSINNUS_USER_INACTIVITY_SCHEDULE['days'], seconds=1)
        with freeze_time(deactivation_date):
            MarkInactiveUsersForDeletion().do()
            self.test_user.cosinnus_profile.refresh_from_db()
            self.assertIsNone(self.test_user.cosinnus_profile.scheduled_for_deletion_at)
            send_mail_mock.assert_called_once_with(
                self.test_user,
                'Attention: Your profile has been deactivated and will be deleted due to inactivity',
                ANY,
                threaded=False,
                raise_on_error=True,
            )
            send_mail_mock.reset_mock()

    def test_admin_reassignment_other_user(self):
        cache.clear()  # clear membership cache
        second_user = create_active_test_user('user2')
        test_group = CosinnusSociety.objects.create(name='Test Group')
        CosinnusGroupMembership.objects.create(group=test_group, user=self.test_user, status=MEMBERSHIP_ADMIN)
        CosinnusGroupMembership.objects.create(group=test_group, user=second_user, status=MEMBERSHIP_MEMBER)

        last_login = datetime(2014, 1, 1, tzinfo=timezone.utc)
        self.test_user.last_login = last_login
        self.test_user.save()

        deactivation_date = last_login + timedelta(days=settings.COSINNUS_USER_INACTIVITY_SCHEDULE['days'], seconds=1)
        with freeze_time(deactivation_date):
            MarkInactiveUsersForDeletion().do()
            test_group.refresh_from_db()
            self.assertIsNone(test_group.scheduled_for_deletion_at)
            self.assertIn(second_user.pk, test_group.admins)

    def test_admin_reassignment_single_user(self):
        cache.clear()  # clear membership cache
        test_group = CosinnusSociety.objects.create(name='Test Group')
        CosinnusGroupMembership.objects.create(group=test_group, user=self.test_user, status=MEMBERSHIP_ADMIN)

        last_login = datetime(2014, 1, 1, tzinfo=timezone.utc)
        self.test_user.last_login = last_login
        self.test_user.save()

        deactivation_date = last_login + timedelta(days=settings.COSINNUS_USER_INACTIVITY_SCHEDULE['days'], seconds=1)
        expected_deletion = deactivation_date + timedelta(days=settings.COSINNUS_GROUP_DELETION_SCHEDULE_DAYS)
        with freeze_time(deactivation_date):
            self.assertTrue(test_group.is_active)
            MarkInactiveUsersForDeletion().do()
            test_group.refresh_from_db()
            self.assertFalse(test_group.is_active)
            self.assertEqual(test_group.scheduled_for_deletion_at, expected_deletion)

    def test_admin_reassignment_other_admins(self):
        cache.clear()  # clear membership cache
        second_admin = create_active_test_user('admin2')
        test_group = CosinnusSociety.objects.create(name='Test Group')
        CosinnusGroupMembership.objects.create(group=test_group, user=self.test_user, status=MEMBERSHIP_ADMIN)
        CosinnusGroupMembership.objects.create(group=test_group, user=second_admin, status=MEMBERSHIP_ADMIN)

        last_login = datetime(2014, 1, 1, tzinfo=timezone.utc)
        self.test_user.last_login = last_login
        self.test_user.save()

        deactivation_date = last_login + timedelta(days=settings.COSINNUS_USER_INACTIVITY_SCHEDULE['days'], seconds=1)
        with freeze_time(deactivation_date):
            self.assertTrue(test_group.is_active)
            self.assertIn(second_admin.pk, test_group.admins)
            MarkInactiveUsersForDeletion().do()
            test_group.refresh_from_db()
            self.assertTrue(test_group.is_active)
            self.assertIn(second_admin.pk, test_group.admins)


class InactivityPreviewTest(TestUserMixin, TestCase):
    def login_as_superuser(self):
        self.test_user.is_superuser = True
        self.test_user.save()
        self.client.force_login(self.test_user)

    @override_settings(
        LANGUAGES=(('de', 'Deutsch'), ('en', 'English')),
        COSINNUS_USER_INACTIVITY_SCHEDULE={
            'days': 3650,
            'warnings': {
                14: {
                    'subject_template': 'cosinnus/mail/inactivity/user_subject.txt',
                    'body_template': 'cosinnus/mail/inactivity/user_body.txt',
                },
            },
        },
    )
    def test_inactivity_preview_uses_configured_languages(self):
        self.login_as_superuser()

        response = self.client.get(reverse('cosinnus:housekeeping-inactivity-preview'))

        self.assertEqual(response.status_code, 200)
        previews = response.context['sections'][0]['warnings'][0]['previews']
        self.assertEqual([preview['language'] for preview in previews], ['de', 'en'])

    @override_settings(
        LANGUAGES=(('en', 'English'),),
        COSINNUS_USER_INACTIVITY_SCHEDULE={
            'days': 3650,
            'text': 'custom inactivity period',
            'warnings': {
                14: {
                    'text': 'custom warning period',
                    'subject_template': 'cosinnus/mail/inactivity/user_subject.txt',
                    'body_template': 'cosinnus/mail/inactivity/user_body.txt',
                }
            },
        },
    )
    def test_inactivity_preview_uses_text_overrides(self):
        self.login_as_superuser()

        response = self.client.get(reverse('cosinnus:housekeeping-inactivity-preview'))

        section = response.context['sections'][0]
        self.assertEqual(
            section['inactivity_durations'][0]['values']['used'],
            'custom inactivity period',
        )
        self.assertEqual(
            section['warnings'][0]['previews'][0]['warning_duration']['used'],
            'custom warning period',
        )

    def test_inactivity_preview_requires_superuser(self):
        self.client.force_login(self.test_user)

        response = self.client.get(reverse('cosinnus:housekeeping-inactivity-preview'))

        self.assertEqual(response.status_code, 403)


class TestGroupMixin:
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        with freeze_time('2024-01-01'):
            cls.test_admin = create_active_test_user('admin')
            cls.test_member = create_active_test_user('member')
            cls.test_group = CosinnusSociety.objects.create(name='Test Group')
            cls.admin_membership = CosinnusGroupMembership.objects.create(
                group=cls.test_group, user=cls.test_admin, status=MEMBERSHIP_ADMIN
            )
            cls.user_membership = CosinnusGroupMembership.objects.create(
                group=cls.test_group, user=cls.test_member, status=MEMBERSHIP_MEMBER
            )


class GroupDeletionTest(TestGroupMixin, TestCase):
    def test_group_delete_cron_job(self):
        self.test_group.scheduled_for_deletion_at = datetime(2024, 2, 1)
        self.test_group.save()

        # group is not deleted before the scheduled time
        with freeze_time('2024-01-31'):
            DeleteScheduledGroups().do()
            self.assertTrue(CosinnusSociety.objects.filter(pk=self.test_group.pk).exists())

        # active group are not deleted at scheduled time
        with freeze_time('2024-02-1'):
            DeleteScheduledGroups().do()
            self.assertTrue(CosinnusSociety.objects.filter(pk=self.test_group.pk).exists())

        # inactive groups are deleted at scheduled time
        self.test_group.is_active = False
        self.test_group.save()
        with freeze_time('2024-02-1'):
            DeleteScheduledGroups().do()
            self.assertFalse(CosinnusSociety.objects.filter(pk=self.test_group.pk).exists())

    def test_reactivating_group_aborts_deletion(self):
        self.test_group.is_active = False
        self.test_group.save()
        self.test_group.scheduled_for_deletion_at = now()
        self.test_group.is_active = True
        self.test_group.save()
        self.test_group.refresh_from_db()
        self.assertIsNone(self.test_group.scheduled_for_deletion_at)

    def test_forum_cannot_be_marked_for_deletion(self):
        self.test_group.name = settings.NEWW_FORUM_GROUP_SLUG
        self.test_group.slug = settings.NEWW_FORUM_GROUP_SLUG
        self.test_group.save()

        self.assertTrue(self.test_group.is_active)
        self.assertIsNone(self.test_group.scheduled_for_deletion_at)

        # try to delete group
        mark_group_for_deletion(self.test_group)

        # check that the group is still active and not scheduled for deletion
        self.assertTrue(self.test_group.is_active)
        self.assertIsNone(self.test_group.scheduled_for_deletion_at)


class GroupManualDeletionTest(TestGroupMixin, TestCase):
    @freeze_time('2024-01-01')
    def test_group_delete_view_schedules_deletion(self):
        self.client.force_login(self.test_admin)
        self.assertTrue(self.test_group.is_active)
        self.assertIsNone(self.test_group.scheduled_for_deletion_at)

        # delete group
        delete_url = group_aware_reverse('cosinnus:group-schedule-delete', kwargs={'group': self.test_group})
        response = self.client.post(delete_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(reverse('cosinnus:user-dashboard'), response.get('location'))
        self.test_group.refresh_from_db()

        # check that the group is deactivated and scheduled for deletion
        self.assertFalse(self.test_group.is_active)
        expected_deletion_at = now() + timedelta(days=settings.COSINNUS_GROUP_DELETION_SCHEDULE_DAYS)
        self.assertEqual(self.test_group.scheduled_for_deletion_at, expected_deletion_at)


_DEACTIVATION_DAYS = 365 * 10  # 10 years
_NOTIFICATION_ONE_YEAR_DAYS = 365
_GROUP_INACTIVITY_SCHEDULE = {
    'days': _DEACTIVATION_DAYS,
    'warnings': {
        _NOTIFICATION_ONE_YEAR_DAYS: {
            'text': '1 year',
            'subject_template': 'cosinnus/mail/inactivity/group_subject.txt',
            'body_template': 'cosinnus/mail/inactivity/group_body.txt',
        },
        182: {
            'text': '6 months',
            'subject_template': 'cosinnus/mail/inactivity/group_subject.txt',
            'body_template': 'cosinnus/mail/inactivity/group_body.txt',
        },
        14: {
            'text': '2 weeks',
            'subject_template': 'cosinnus/mail/inactivity/group_subject.txt',
            'body_template': 'cosinnus/mail/inactivity/group_body.txt',
        },
        2: {
            'text': '2 days',
            'subject_template': 'cosinnus/mail/inactivity/group_subject.txt',
            'body_template': 'cosinnus/mail/inactivity/group_body.txt',
        },
    },
}


class GroupInactivityDeletionTest(TestGroupMixin, TestCase):
    """Test last activity calculation for groups with the cronjob `UpdateGroupsLastActivity` that should
    only re-calculate group.last_activity very rarely before it becomes relevant.
    """

    def setUp(self):
        # define freezable dates
        self.initial_activity_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        self.relevant_recalculation_time = self.initial_activity_time + timedelta(_DEACTIVATION_DAYS - 1)
        super().setUp()

    @override_settings(
        COSINNUS_USER_INACTIVITY_SCHEDULE={'days': 10, 'warnings': {}},
        COSINNUS_GROUP_INACTIVITY_SCHEDULE={'days': 20, 'warnings': {}},
    )
    def test_user_and_group_use_separate_inactivity_schedules(self):
        with freeze_time('2024-01-16'):
            self.assertIn(self.test_admin, get_users_due_for_inactivity_deactivation())
            self.assertNotIn(self.test_group, get_groups_due_for_inactivity_deactivation())

    @override_settings(
        COSINNUS_GROUP_INACTIVITY_SCHEDULE=_GROUP_INACTIVITY_SCHEDULE,
        COSINNUS_INACTIVE_DEACTIVATION_ACTIVITY_COMPUTATION_WINDOW_DAYS=3,
    )
    def test_group_last_activity_update_windows(self):
        """A test that tests whether the `update_group_last_activity` updates properly only do their expensive
          calculations via cronjob `UpdateGroupsLastActivity` at specific days and will not do anything at other times.

        Test explanation: we make a change to a group, then freeze time to outside of the windows of calculation and run
          UpdateGroupsLastActivity().do() and the date should not change, and then we freeze to within the intended time
          windows of calculation and run UpdateGroupsLastActivity().do() and the last_activity date should change!
        """

        # newly created groups should always have last_activity set to their creation date
        self.test_group.refresh_from_db()
        self.assertIsNotNone(self.test_group.last_activity, 'newly created group last_activity is not None')

        # set last activity to 01.01.2024 because the new creation of the group will have set it to the test's timestamp
        self.test_group.last_activity = self.initial_activity_time
        type(self.test_group).objects.filter(pk=self.test_group.pk).update(last_activity=self.test_group.last_activity)

        # test activity calculation with last modified: at a point time where we are not in the re-calculation time
        activity_time_at_edit = datetime(2024, 6, 1, tzinfo=timezone.utc)
        with freeze_time(activity_time_at_edit):
            self.assertEqual(self.test_group.last_activity, self.initial_activity_time)
            self.test_group.name = 'edited'
            self.test_group.save()
            UpdateGroupsLastActivity().do()
            self.test_group.refresh_from_db()
            self.assertEqual(self.test_group.last_modified, activity_time_at_edit, 'group.last_modified was updated')
            self.assertEqual(
                self.test_group.last_activity, self.initial_activity_time, 'last_activity was not recalculated'
            )

        # now test recalculation same while we're at a timepoint just before the deletion date,
        # so re-calculation should happen
        with freeze_time(self.relevant_recalculation_time):
            self.assertEqual(self.test_group.last_activity, self.initial_activity_time)
            UpdateGroupsLastActivity().do()
            self.test_group.refresh_from_db()
            self.assertEqual(
                self.test_group.last_modified, activity_time_at_edit, 'group.last_modified is still correct'
            )
            self.assertEqual(
                self.test_group.last_activity,
                activity_time_at_edit,
                'last_activity was recalculated and is the time of the group name edit',
            )

        # a timeslot before deletion notification is also relevant
        self.test_group.last_activity = self.initial_activity_time  # reset initial activity time
        type(self.test_group).objects.filter(pk=self.test_group.pk).update(last_activity=self.test_group.last_activity)
        notification_relevant_recalculation_time = self.initial_activity_time + timedelta(
            (_DEACTIVATION_DAYS - _NOTIFICATION_ONE_YEAR_DAYS) - 1
        )
        with freeze_time(notification_relevant_recalculation_time):
            self.assertEqual(self.test_group.last_activity, self.initial_activity_time)
            UpdateGroupsLastActivity().do()
            self.test_group.refresh_from_db()
            self.assertEqual(
                self.test_group.last_activity,
                activity_time_at_edit,
                'last_activity was recalculated near notification time and is the time of the edit',
            )

    @override_settings(
        COSINNUS_GROUP_INACTIVITY_SCHEDULE=_GROUP_INACTIVITY_SCHEDULE,
        COSINNUS_INACTIVE_DEACTIVATION_ACTIVITY_COMPUTATION_WINDOW_DAYS=3,
    )
    def test_group_last_activity_calculation(self):
        """A test that tests whether both the instant triggers and the `update_group_last_activity` updates
        via cronjob `UpdateGroupsLastActivity` reflect the logic of updating a group's `last_activity` date field
        when there was relevant activity within that group."""

        # test new memberships (Calculation within recalcuation time period)
        self.test_group.last_activity = self.initial_activity_time  # reset initial activity time
        type(self.test_group).objects.filter(pk=self.test_group.pk).update(last_activity=self.test_group.last_activity)
        activity_time = datetime(2024, 7, 1, tzinfo=timezone.utc)
        with freeze_time(activity_time):
            new_member = create_active_test_user('new1')
            new_membership = CosinnusGroupMembership.objects.create(
                group=self.test_group, user=new_member, status=MEMBERSHIP_MEMBER
            )
        self.assertEqual(
            self.test_group.last_activity,
            activity_time,
            'last activity was instantly updated via the new membership creation trigger',
        )
        # reset to initial activity time to now test the cronjob setting the last activity, instead of the save trigger
        self.test_group.last_activity = self.initial_activity_time
        type(self.test_group).objects.filter(pk=self.test_group.pk).update(last_activity=self.test_group.last_activity)
        # test membership status changes
        activity_time = datetime(2024, 7, 2, tzinfo=timezone.utc)
        with freeze_time(activity_time):
            new_membership.save()
        self.assertEqual(
            self.test_group.last_activity,
            self.initial_activity_time,
            'a membership save without status change does not cause last_activity to update',
        )
        activity_time = datetime(2024, 7, 3, tzinfo=timezone.utc)
        with freeze_time(activity_time):
            new_membership.status = MEMBERSHIP_PENDING
            new_membership.save()
            new_membership.status = MEMBERSHIP_MEMBER
            new_membership.save()
        self.assertEqual(
            self.test_group.last_activity,
            activity_time,
            'but a membership save that becomes a member does cause last_activity to update',
        )
        # test cronjob to recognize new memberships as update criteria, reset group's last_activity time
        self.test_group.last_activity = self.initial_activity_time
        type(self.test_group).objects.filter(pk=self.test_group.pk).update(last_activity=self.test_group.last_activity)
        with freeze_time(self.relevant_recalculation_time):
            UpdateGroupsLastActivity().do()
            self.test_group.refresh_from_db()
            self.assertEqual(
                self.test_group.last_activity,
                activity_time,
                'a new membership caused an updated last_activity via the cronjob',
            )

        # reset to initial activity time to test cronjob to NOT recognize new membership *requests* as update criteria
        activity_time = datetime(2024, 8, 1, tzinfo=timezone.utc)
        with freeze_time(activity_time):
            new_membership.status = MEMBERSHIP_PENDING
            new_membership.save()
        self.test_group.last_activity = self.initial_activity_time
        type(self.test_group).objects.filter(pk=self.test_group.pk).update(last_activity=self.test_group.last_activity)
        self.assertEqual(
            self.test_group.last_activity,
            self.initial_activity_time,
            'we have properly reset the initial time',
        )
        with freeze_time(self.relevant_recalculation_time):
            UpdateGroupsLastActivity().do()
            self.test_group.refresh_from_db()
            self.assertEqual(
                self.test_group.last_activity,
                self.initial_activity_time,
                'a new membership *request* did not cause an updated last_activity via the cronjob',
            )

        # test tagged objects (Calculation within recalcuation time period)
        self.test_group.last_activity = self.initial_activity_time  # reset initial activity time
        type(self.test_group).objects.filter(pk=self.test_group.pk).update(last_activity=self.test_group.last_activity)
        activity_time = datetime(2024, 8, 2, tzinfo=timezone.utc)
        with freeze_time(activity_time):
            Note.objects.create(text='Test Note', group=self.test_group, creator=self.test_member)
        self.assertEqual(
            self.test_group.last_activity,
            activity_time,
            'last activity was instantly updated via the new tagged object creation trigger',
        )
        # reset to initial activity time to now the cronjob setting the last activity, instead of the save trigger
        self.test_group.last_activity = self.initial_activity_time
        type(self.test_group).objects.filter(pk=self.test_group.pk).update(last_activity=self.test_group.last_activity)
        with freeze_time(self.relevant_recalculation_time):
            UpdateGroupsLastActivity().do()
            self.test_group.refresh_from_db()
            self.assertEqual(
                self.test_group.last_activity,
                activity_time,
                'a new tagged object caused an updated last_activity via the cronjob',
            )

    @override_settings(
        COSINNUS_GROUP_INACTIVITY_SCHEDULE=_GROUP_INACTIVITY_SCHEDULE,
        COSINNUS_INACTIVE_DEACTIVATION_ACTIVITY_COMPUTATION_WINDOW_DAYS=3,
    )
    def test_group_last_activity_constraints(self):
        """A test that tests whether the `update_group_last_activity` updates run properly (or not) depending on
        different group properties or states."""

        # Constraint-test: no last_activity calculation for inactive groups if their activity is already set
        self.test_group.is_active = False
        self.test_group.last_activity = self.initial_activity_time  # reset initial activity time
        type(self.test_group).objects.filter(pk=self.test_group.pk).update(
            last_activity=self.test_group.last_activity, is_active=self.test_group.is_active
        )
        self.assertFalse(self.test_group.is_active)
        unchanged_activity_time = self.test_group.last_activity
        activity_time = datetime(2024, 9, 1, tzinfo=timezone.utc)
        with freeze_time(activity_time):
            self.assertIsNotNone(self.test_group.last_activity)
            self.assertNotEqual(self.test_group.last_activity, activity_time)
            # adding a member would would cause an updated last_activity if recalculated, IF the group was active
            new_member = create_active_test_user('new2')
            CosinnusGroupMembership.objects.create(group=self.test_group, user=new_member, status=MEMBERSHIP_MEMBER)
        # reset to initial activity time to now the cronjob setting the last activity, instead of the save trigger
        self.test_group.last_activity = self.initial_activity_time
        type(self.test_group).objects.filter(pk=self.test_group.pk).update(last_activity=self.test_group.last_activity)
        with freeze_time(self.relevant_recalculation_time):
            UpdateGroupsLastActivity().do()
            self.test_group.refresh_from_db()
            self.assertNotEqual(
                self.test_group.last_activity, activity_time, 'no recalculation happened for an inactive group'
            )
            self.assertEqual(
                self.test_group.last_activity,
                unchanged_activity_time,
                'group.last_activity stayed the same for an inactive group',
            )

        # but inactive groups ARE calculated if no last_activity is set
        # (this update is caused from the new membership created with `create_active_test_user('new2')` above)
        self.test_group.is_active = False
        self.test_group.last_activity = None
        type(self.test_group).objects.filter(pk=self.test_group.pk).update(
            last_activity=self.test_group.last_activity, is_active=self.test_group.is_active
        )
        with freeze_time(self.relevant_recalculation_time):
            UpdateGroupsLastActivity().do()
            self.test_group.refresh_from_db()
            self.assertEqual(
                self.test_group.last_activity,
                activity_time,
                'recalculation has happened for an inactive group that had no last_activity set',
            )

    @patch('cosinnus.views.group_deletion.update_group_last_activity')
    def test_group_last_activity_update_skips_forum(self, update_group_activity_mock):
        self.test_group.name = settings.NEWW_FORUM_GROUP_SLUG
        self.test_group.slug = settings.NEWW_FORUM_GROUP_SLUG
        self.test_group.last_activity = None
        self.test_group.save()
        self.assertIsNone(self.test_group.last_activity)
        UpdateGroupsLastActivity().do()
        self.assertFalse(update_group_activity_mock.called)
        self.test_group.refresh_from_db()
        self.assertIsNone(self.test_group.last_activity)

    @patch('cosinnus.views.group_deletion.send_html_mail')
    def test_inactivity_notifications(self, send_mail_mock):
        last_activity = datetime(2014, 1, 1)
        with freeze_time(last_activity):
            self.test_group.last_activity = last_activity
            self.test_group.save()

        schedule = settings.COSINNUS_GROUP_INACTIVITY_SCHEDULE
        deactivation_date = last_activity + timedelta(days=schedule['days'])
        for days_before_deactivation, warning_config in schedule['warnings'].items():
            notification_date = deactivation_date - timedelta(days=days_before_deactivation)

            # no notification is sent the day before scheduled date
            day_before_notification = notification_date - timedelta(days=1)
            with freeze_time(day_before_notification):
                SendGroupsInactivityNotifications().do()
                self.assertFalse(send_mail_mock.called)

            # admin notification is sent at the scheduled date
            with freeze_time(notification_date):
                SendGroupsInactivityNotifications().do()
                send_mail_mock.assert_called_once_with(
                    self.test_admin,
                    f'{self.test_group.trans.VERBOSE_NAME} {self.test_group.name} will be deleted due to inactivity',
                    ANY,
                    raise_on_error=True,
                )

                # make sure placeholders are filled in mail content
                warning_text = format_inactivity_duration(days_before_deactivation, warning_config, 'en')
                inactivity_text = format_inactivity_duration(schedule['days'], schedule, 'en')
                mail_body = send_mail_mock.call_args.args[2]
                self.assertIn(f'will be deactivated {inactivity_text} after the last activity', mail_body)
                self.assertIn(f'This will happen in {warning_text}', mail_body)
                send_mail_mock.reset_mock()

                # notification is not send again
                SendGroupsInactivityNotifications().do()
                self.assertFalse(send_mail_mock.called)

            # no notification is sent the day after scheduled date, if not enabled by settings
            # CHECKS BEFORE/AFTER

            if (days_before_deactivation - 1) not in settings.COSINNUS_GROUP_INACTIVITY_SCHEDULE['warnings']:
                day_after_notification = notification_date + timedelta(days=1)
                with freeze_time(day_after_notification):
                    SendGroupsInactivityNotifications().do()
                    self.assertFalse(send_mail_mock.called)

    @override_settings(COSINNUS_INACTIVITY_DRY_RUN=True)
    @patch('cosinnus.views.group_deletion.send_html_mail')
    def test_inactivity_dry_run_notification(self, send_mail_mock):
        schedule = settings.COSINNUS_GROUP_INACTIVITY_SCHEDULE
        days_before_deactivation = next(iter(schedule['warnings']))
        last_activity = datetime(2014, 1, 1)
        notification_date = last_activity + timedelta(days=schedule['days'] - days_before_deactivation)

        self.test_group.last_activity = last_activity
        self.test_group.save()

        with freeze_time(notification_date):
            result = SendGroupsInactivityNotifications().do()

        self.assertEqual(result, '1 groups would be notified (dry run).')
        send_mail_mock.assert_not_called()
        self.test_group.refresh_from_db()
        self.assertIsNone(self.test_group.inactivity_notification_sent_at)

    @override_settings(COSINNUS_INACTIVITY_DRY_RUN=True)
    @patch('cosinnus.views.group_deletion.send_html_mail')
    def test_inactivity_dry_run_deactivation(self, send_mail_mock):
        schedule = settings.COSINNUS_GROUP_INACTIVITY_SCHEDULE
        last_activity = datetime(2014, 1, 1, tzinfo=timezone.utc)
        deactivation_date = last_activity + timedelta(days=schedule['days'], seconds=1)

        self.test_group.last_activity = last_activity
        self.test_group.save()

        with freeze_time(deactivation_date):
            result = MarkInactiveGroupsForDeletion().do()

        self.assertEqual(result, '1 groups would be scheduled for deletion (dry run).')
        send_mail_mock.assert_not_called()
        self.test_group.refresh_from_db()
        self.assertTrue(self.test_group.is_active)
        self.assertIsNone(self.test_group.scheduled_for_deletion_at)

    @patch('cosinnus.views.group_deletion.send_html_mail')
    def test_scheduled_deletion(self, send_mail_mock):
        last_activity = datetime(2014, 1, 1, tzinfo=timezone.utc)
        self.test_group.last_activity = last_activity
        self.test_group.save()

        deactivation_date = last_activity + timedelta(
            days=settings.COSINNUS_GROUP_INACTIVITY_SCHEDULE['days'], seconds=1
        )

        # do not schedule before date
        day_before_deactivation = deactivation_date - timedelta(days=1)
        with freeze_time(day_before_deactivation):
            MarkInactiveGroupsForDeletion().do()
            self.test_group.refresh_from_db()
            self.assertIsNone(self.test_group.scheduled_for_deletion_at)
            self.assertFalse(send_mail_mock.called)

        # deletion is scheduled after the schedule interval is passed
        expected_deletion = deactivation_date + timedelta(days=settings.COSINNUS_GROUP_DELETION_SCHEDULE_DAYS)
        with freeze_time(deactivation_date):
            MarkInactiveGroupsForDeletion().do()
            self.test_group.refresh_from_db()
            self.assertEqual(self.test_group.scheduled_for_deletion_at, expected_deletion)
            self.assertEqual(send_mail_mock.call_count, 2)
            send_mail_mock.assert_any_call(
                self.test_admin,
                f'Group {self.test_group.name} has been deactivated and will be deleted',
                ANY,
                raise_on_error=True,
            )
            send_mail_mock.assert_any_call(
                self.test_member,
                f'Group {self.test_group.name} has been deactivated and will be deleted',
                ANY,
                raise_on_error=True,
            )
            send_mail_mock.reset_mock()

        # do not reschedule already scheduled deletions
        day_after_deactivation = deactivation_date + timedelta(days=1)
        with freeze_time(day_after_deactivation):
            self.assertEqual(self.test_group.scheduled_for_deletion_at, expected_deletion)
            MarkInactiveGroupsForDeletion().do()
            self.test_group.refresh_from_db()
            self.assertEqual(self.test_group.scheduled_for_deletion_at, expected_deletion)

    @override_settings(
        COSINNUS_GROUP_INACTIVITY_SCHEDULE={
            'days': 3650,
            'warnings': {},
        },
    )
    @patch('cosinnus.views.group_deletion.send_html_mail')
    def test_deactivation_mails_use_recipient_languages(self, send_mail_mock):
        # The admin receives German mail, while the member keeps the default English language.
        self.test_admin.cosinnus_profile.language = 'de'
        self.test_admin.cosinnus_profile.save()
        self.test_group.last_activity = now() - timedelta(days=3651)
        self.test_group.save()

        # Record the active language at the point each recipient's mail is sent.
        sent_languages = []
        send_mail_mock.side_effect = lambda *args, **kwargs: sent_languages.append(translation.get_language())

        # Per-recipient overrides must not leak into the surrounding language context.
        with translation.override('en'):
            mark_group_for_deletion(self.test_group)
            self.assertEqual(translation.get_language(), 'en')

        self.assertCountEqual(sent_languages, ['de', 'en'])

    @patch('cosinnus.views.group_deletion.send_html_mail')
    def test_scheduled_deletion_of_inactive_groups(self, send_mail_mock):
        last_activity = datetime(2014, 1, 1, tzinfo=timezone.utc)
        self.test_group.is_active = False
        self.test_group.last_activity = last_activity
        self.test_group.save()

        deactivation_date = last_activity + timedelta(
            days=settings.COSINNUS_GROUP_INACTIVITY_SCHEDULE['days'], seconds=1
        )

        # deletion is scheduled after the schedule interval is passed
        expected_deletion = deactivation_date + timedelta(days=settings.COSINNUS_GROUP_DELETION_SCHEDULE_DAYS)
        with freeze_time(deactivation_date):
            MarkInactiveGroupsForDeletion().do()
            self.test_group.refresh_from_db()
            self.assertEqual(self.test_group.scheduled_for_deletion_at, expected_deletion)
            send_mail_mock.assert_called_once_with(
                self.test_admin,
                f'Group {self.test_group.name} has been deactivated and will be deleted',
                ANY,
                raise_on_error=True,
            )
            send_mail_mock.reset_mock()
