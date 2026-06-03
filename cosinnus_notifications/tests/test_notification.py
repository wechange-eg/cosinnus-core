from dataclasses import dataclass

from django.test import TestCase

from cosinnus.conf import settings
from cosinnus.core.middleware.cosinnus_middleware import initialize_cosinnus_after_startup
from cosinnus.models import GlobalUserNotificationSetting
from cosinnus.tests.factories import ActiveUserFactory, CosinnusSocietyFactory, NoteFactory
from cosinnus.utils.group import get_default_user_group_ids
from cosinnus_notifications.notifications import NotificationsThread

SETTING_NEVER = GlobalUserNotificationSetting.SETTING_NEVER
SETTING_NOW = GlobalUserNotificationSetting.SETTING_NOW
SETTING_DAILY = GlobalUserNotificationSetting.SETTING_DAILY
SETTING_WEEKLY = GlobalUserNotificationSetting.SETTING_WEEKLY
SETTING_INDIVIDUAL = GlobalUserNotificationSetting.SETTING_GROUP_INDIVIDUAL

NOTE_CREATED = 'note__note_created'
GROUP_INVITED = 'cosinnus__user_group_invited'

# initialization necessary to populate available notification types
initialize_cosinnus_after_startup()


# define combinations of settings, groups and expected results as matrix for use in subtests
@dataclass(frozen=True)
class Case:
    global_: int
    """global notification-setting"""
    portal: int
    """global portal-group notification-setting"""
    user_group: bool
    """expected result for user_groups"""
    forum: bool
    """expected result for portal default groups"""


SETTING_CASES = [
    Case(global_=SETTING_NOW, portal=SETTING_NOW, user_group=True, forum=True),
    Case(global_=SETTING_NOW, portal=SETTING_DAILY, user_group=True, forum=False),
    Case(global_=SETTING_NOW, portal=SETTING_WEEKLY, user_group=True, forum=False),
    Case(global_=SETTING_NOW, portal=SETTING_NEVER, user_group=True, forum=False),
    Case(global_=SETTING_DAILY, portal=SETTING_NOW, user_group=False, forum=True),
    Case(global_=SETTING_DAILY, portal=SETTING_DAILY, user_group=False, forum=False),
    Case(global_=SETTING_DAILY, portal=SETTING_WEEKLY, user_group=False, forum=False),
    Case(global_=SETTING_DAILY, portal=SETTING_NEVER, user_group=False, forum=False),
    Case(global_=SETTING_WEEKLY, portal=SETTING_NOW, user_group=False, forum=True),
    Case(global_=SETTING_WEEKLY, portal=SETTING_DAILY, user_group=False, forum=False),
    Case(global_=SETTING_WEEKLY, portal=SETTING_WEEKLY, user_group=False, forum=False),
    Case(global_=SETTING_WEEKLY, portal=SETTING_NEVER, user_group=False, forum=False),
    Case(global_=SETTING_NEVER, portal=SETTING_NOW, user_group=False, forum=False),
    Case(global_=SETTING_NEVER, portal=SETTING_DAILY, user_group=False, forum=False),
    Case(global_=SETTING_NEVER, portal=SETTING_WEEKLY, user_group=False, forum=False),
    Case(global_=SETTING_NEVER, portal=SETTING_NEVER, user_group=False, forum=False),
    Case(global_=SETTING_INDIVIDUAL, portal=SETTING_NOW, user_group=False, forum=True),
    Case(global_=SETTING_INDIVIDUAL, portal=SETTING_DAILY, user_group=False, forum=False),
    Case(global_=SETTING_INDIVIDUAL, portal=SETTING_WEEKLY, user_group=False, forum=False),
    Case(global_=SETTING_INDIVIDUAL, portal=SETTING_NEVER, user_group=False, forum=False),
]

SETTING_LABELS = {0: 'NEVER', 1: 'NOW', 2: 'DAILY', 3: 'WEEKLY', 4: 'INDIVIDUAL'}


class NotificationThreadTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.creator = ActiveUserFactory()
        cls.recipient = ActiveUserFactory()

        cls.user_group = CosinnusSocietyFactory(members=[cls.creator, cls.recipient])

        forum_slug = getattr(settings, 'NEWW_FORUM_GROUP_SLUG', None)
        cls.forum = CosinnusSocietyFactory(name='Forum', slug=forum_slug, members=[cls.creator, cls.recipient])

        # clear the cache of the utility function to have the new forum group show up as a default group
        get_default_user_group_ids.cache_clear()
        cls.addClassCleanup(get_default_user_group_ids.cache_clear)

        cls.user_group_note = NoteFactory(group=cls.user_group, creator=cls.creator)
        cls.forum_note = NoteFactory(group=cls.forum, creator=cls.creator)

    def set_recipient_notification_settings(self, global_setting, portal_group_setting):
        settings_obj = GlobalUserNotificationSetting.objects.get_object_for_user(self.recipient)
        settings_obj.portal_group_setting = portal_group_setting
        settings_obj.setting = global_setting
        settings_obj.save()

    def assert_user_wants_notification(self, obj):
        thread = NotificationsThread(
            sender=None,
            user=self.creator,
            obj=obj,
            audience=[self.recipient],
            notification_id=NOTE_CREATED,
            options={},
        )
        thread.group = obj.group
        return thread.check_user_wants_notification(
            self.recipient,
            NOTE_CREATED,
            obj,
        )

    def test_all_global_notification_settings_filtering(self):
        # for each case we check both groups
        group_cases = [
            ('user_group', self.user_group, self.user_group_note, 'user_group'),
            ('forum', self.forum, self.forum_note, 'forum'),
        ]

        for case in SETTING_CASES:
            self.set_recipient_notification_settings(global_setting=case.global_, portal_group_setting=case.portal)
            for group_name, group, note, expected_attr in group_cases:
                with self.subTest(
                    gobal_setting=SETTING_LABELS[case.global_],
                    portal_group_setting=SETTING_LABELS[case.portal],
                    group=group_name,
                ):
                    wants_notification = self.assert_user_wants_notification(obj=note)
                    expected_result = getattr(case, expected_attr)
                    self.assertEqual(wants_notification, expected_result)
