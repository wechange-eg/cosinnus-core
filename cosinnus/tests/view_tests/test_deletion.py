from datetime import datetime, timedelta, timezone
from unittest.mock import ANY, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils.timezone import now
from freezegun import freeze_time

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
from cosinnus.models.group import MEMBERSHIP_ADMIN, MEMBERSHIP_MEMBER, CosinnusGroupMembership
from cosinnus.models.group_extra import CosinnusSociety
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.views.profile_deletion import delete_userprofile
from cosinnus_note.models import Note

# Patch threads as threads do not work with Django tests as they don't get the correct test database connection.
cosinnus_notifications.notifications.NotificationsThread.start = lambda self: self.run()


def create_active_test_user(username='user'):
    test_user_data = {'username': username, 'email': 'testuser@example.com', 'first_name': 'Test', 'last_name': 'User'}
    test_user = get_user_model().objects.create(**test_user_data)
    test_user.last_login = now()
    test_user.save()
    test_user.cosinnus_profile.tos_accepted = True
    test_user.cosinnus_profile.save()
    return test_user


class TestUserMixin:
    def setUp(self):
        self.test_user = create_active_test_user()


class UserDeletionTest(TestUserMixin, TestCase):
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
        self.assertEqual(reverse('login'), response.get('location'))
        self.test_user.refresh_from_db()

        # check the user is deactivated and scheduled for deletion
        self.assertFalse(self.test_user.is_active)
        expected_deletion_at = now() + timedelta(days=settings.COSINNUS_USER_PROFILE_DELETION_SCHEDULE_DAYS)
        self.assertEqual(self.test_user.cosinnus_profile.scheduled_for_deletion_at, expected_deletion_at)

        # check that a notification email was send
        send_mail_mock.assert_called_with(
            self.test_user, 'Information about the deletion of your user account', ANY, threaded=False
        )
        send_mail_mock.reset_mock()


class UserInactivityDeletionTest(TestUserMixin, TestCase):
    @patch('cosinnus.views.profile_deletion.send_html_mail')
    def test_inactivity_notifications(self, send_mail_mock):
        last_login = datetime(2014, 1, 1)
        self.test_user.last_login = last_login
        self.test_user.save()

        deactivation_date = last_login + timedelta(days=settings.COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE)
        for days_before_deactivation, _ in settings.COSINNUS_INACTIVE_NOTIFICATIONS_BEFORE_DEACTIVATION.items():
            notification_date = deactivation_date - timedelta(days=days_before_deactivation)

            # no notification is sent the day before scheduled date
            day_before_notification = notification_date - timedelta(days=1)
            with freeze_time(day_before_notification):
                SendUserInactivityNotifications().do()
                self.assertFalse(send_mail_mock.called)

            # notification is sent at the scheduled date
            with freeze_time(notification_date):
                SendUserInactivityNotifications().do()
                send_mail_mock.assert_called_with(self.test_user, 'Your account will be deleted due to inactivity', ANY)
                send_mail_mock.reset_mock()

                # notification is not send again
                SendUserInactivityNotifications().do()
                self.assertFalse(send_mail_mock.called)

            # no notification is sent the day after scheduled date
            day_after_notification = notification_date + timedelta(days=1)
            with freeze_time(day_after_notification):
                SendUserInactivityNotifications().do()
                self.assertFalse(send_mail_mock.called)

    @patch('cosinnus.views.profile_deletion.send_html_mail')
    def test_scheduled_deletion(self, send_mail_mock):
        last_login = datetime(2014, 1, 1, tzinfo=timezone.utc)
        self.test_user.last_login = last_login
        self.test_user.save()

        deactivation_date = last_login + timedelta(days=settings.COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE, seconds=1)

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
            send_mail_mock.assert_called_with(
                self.test_user,
                'Attention: Your profile has been deactivated will be deleted due to inactivity',
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

    @patch('cosinnus.views.profile_deletion.send_html_mail', side_effect=Exception)
    def test_scheduled_deletion_email_exception(self, send_mail_mock):
        last_login = datetime(2014, 1, 1, tzinfo=timezone.utc)
        self.test_user.last_login = last_login
        self.test_user.save()

        deactivation_date = last_login + timedelta(days=settings.COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE, seconds=1)
        with freeze_time(deactivation_date):
            MarkInactiveUsersForDeletion().do()
            self.test_user.cosinnus_profile.refresh_from_db()
            self.assertIsNone(self.test_user.cosinnus_profile.scheduled_for_deletion_at)
            send_mail_mock.assert_called_with(
                self.test_user,
                'Attention: Your profile has been deactivated will be deleted due to inactivity',
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

        deactivation_date = last_login + timedelta(days=settings.COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE, seconds=1)
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

        deactivation_date = last_login + timedelta(days=settings.COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE, seconds=1)
        expected_deletion = deactivation_date + timedelta(days=settings.COSINNUS_USER_PROFILE_DELETION_SCHEDULE_DAYS)
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

        deactivation_date = last_login + timedelta(days=settings.COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE, seconds=1)
        with freeze_time(deactivation_date):
            self.assertTrue(test_group.is_active)
            self.assertIn(second_admin.pk, test_group.admins)
            MarkInactiveUsersForDeletion().do()
            test_group.refresh_from_db()
            self.assertTrue(test_group.is_active)
            self.assertIn(second_admin.pk, test_group.admins)


class TestGroupMixin:
    def setUp(self):
        with freeze_time('2024-01-01'):
            self.test_admin = create_active_test_user('admin')
            self.test_member = create_active_test_user('member')
            self.test_group = CosinnusSociety.objects.create(name='Test Group')
            self.admin_membership = CosinnusGroupMembership.objects.create(
                group=self.test_group, user=self.test_admin, status=MEMBERSHIP_ADMIN
            )
            self.user_membership = CosinnusGroupMembership.objects.create(
                group=self.test_group, user=self.test_member, status=MEMBERSHIP_MEMBER
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

        # check the user is deactivated and scheduled for deletion
        self.assertFalse(self.test_group.is_active)
        expected_deletion_at = now() + timedelta(days=settings.COSINNUS_GROUP_DELETION_SCHEDULE_DAYS)
        self.assertEqual(self.test_group.scheduled_for_deletion_at, expected_deletion_at)


class GroupInactivityDeletionTest(TestGroupMixin, TestCase):
    def test_group_last_activity_update(self):
        # test last modified
        activity_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        with freeze_time(activity_time):
            self.test_group.name = 'edited'
            self.test_group.save()
            UpdateGroupsLastActivity().do()
            self.test_group.refresh_from_db()
            self.assertEqual(self.test_group.last_activity, activity_time)

        # test new memberships
        activity_time = datetime(2024, 1, 2, tzinfo=timezone.utc)
        with freeze_time(activity_time):
            new_member = create_active_test_user('new')
            CosinnusGroupMembership.objects.create(group=self.test_group, user=new_member, status=MEMBERSHIP_MEMBER)
            UpdateGroupsLastActivity().do()
            self.test_group.refresh_from_db()
            self.assertEqual(self.test_group.last_activity, activity_time)

        # test tagged objects
        activity_time = datetime(2024, 1, 3, tzinfo=timezone.utc)
        with freeze_time(activity_time):
            Note.objects.create(text='Test Note', group=self.test_group, creator=self.test_member)
            UpdateGroupsLastActivity().do()
            self.test_group.refresh_from_db()
            self.assertEqual(self.test_group.last_activity, activity_time)

    @patch('cosinnus.views.group_deletion.send_html_mail')
    def test_inactivity_notifications(self, send_mail_mock):
        last_activity = datetime(2014, 1, 1)
        with freeze_time(last_activity):
            self.test_group.last_activity = last_activity
            self.test_group.save()

        deactivation_date = last_activity + timedelta(days=settings.COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE)
        for days_before_deactivation, _ in settings.COSINNUS_INACTIVE_NOTIFICATIONS_BEFORE_DEACTIVATION.items():
            notification_date = deactivation_date - timedelta(days=days_before_deactivation)

            # no notification is sent the day before scheduled date
            day_before_notification = notification_date - timedelta(days=1)
            with freeze_time(day_before_notification):
                SendGroupsInactivityNotifications().do()
                self.assertFalse(send_mail_mock.called)

            # admin notification is sent at the scheduled date
            with freeze_time(notification_date):
                SendGroupsInactivityNotifications().do()
                send_mail_mock.assert_called_with(
                    self.test_admin, f'Group {self.test_group.name} will be deleted due to inactivity', ANY
                )
                send_mail_mock.reset_mock()

                # notification is not send again
                SendGroupsInactivityNotifications().do()
                self.assertFalse(send_mail_mock.called)

            # no notification is sent the day after scheduled date
            day_after_notification = notification_date + timedelta(days=1)
            with freeze_time(day_after_notification):
                SendGroupsInactivityNotifications().do()
                self.assertFalse(send_mail_mock.called)

    @patch('cosinnus.views.group_deletion.send_html_mail')
    def test_scheduled_deletion(self, send_mail_mock):
        last_activity = datetime(2014, 1, 1, tzinfo=timezone.utc)
        self.test_group.last_activity = last_activity
        self.test_group.save()

        deactivation_date = last_activity + timedelta(days=settings.COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE, seconds=1)

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
                self.test_admin, f'Group {self.test_group.name} has been deactivated and will be deleted', ANY
            )
            send_mail_mock.assert_any_call(
                self.test_member, f'Group {self.test_group.name} has been deactivated and will be deleted', ANY
            )
            send_mail_mock.reset_mock()

        # do not reschedule already scheduled deletions
        day_after_deactivation = deactivation_date + timedelta(days=1)
        with freeze_time(day_after_deactivation):
            self.assertEqual(self.test_group.scheduled_for_deletion_at, expected_deletion)
            MarkInactiveGroupsForDeletion().do()
            self.test_group.refresh_from_db()
            self.assertEqual(self.test_group.scheduled_for_deletion_at, expected_deletion)

    @patch('cosinnus.views.group_deletion.send_html_mail')
    def test_scheduled_deletion_of_inactive_groups(self, send_mail_mock):
        last_activity = datetime(2014, 1, 1, tzinfo=timezone.utc)
        self.test_group.is_active = False
        self.test_group.last_activity = last_activity
        self.test_group.save()

        deactivation_date = last_activity + timedelta(days=settings.COSINNUS_INACTIVE_DEACTIVATION_SCHEDULE, seconds=1)

        # deletion is scheduled after the schedule interval is passed
        expected_deletion = deactivation_date + timedelta(days=settings.COSINNUS_GROUP_DELETION_SCHEDULE_DAYS)
        with freeze_time(deactivation_date):
            MarkInactiveGroupsForDeletion().do()
            self.test_group.refresh_from_db()
            self.assertEqual(self.test_group.scheduled_for_deletion_at, expected_deletion)
            send_mail_mock.assert_called_with(
                self.test_admin, f'Group {self.test_group.name} has been deactivated and will be deleted', ANY
            )
            send_mail_mock.reset_mock()
