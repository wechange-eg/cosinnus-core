from unittest.mock import patch

from django.test import TestCase

from cosinnus.conf import settings
from cosinnus.core.middleware.cosinnus_middleware import initialize_cosinnus_after_startup
from cosinnus.models import GlobalUserNotificationSetting
from cosinnus.tests.factories import (
    ActiveUserFactory,
    CosinnusSocietyFactory,
    NoteFactory,
)
from cosinnus.utils.group import get_default_user_group_ids
from cosinnus_notifications.digest import send_digest_for_current_portal

# initialization necessary to populate available notification types
initialize_cosinnus_after_startup()

SETTING_WEEKLY = GlobalUserNotificationSetting.SETTING_WEEKLY
SETTING_DAILY = GlobalUserNotificationSetting.SETTING_DAILY
SETTING_NEVER = GlobalUserNotificationSetting.SETTING_NEVER


class TestDigestSending(TestCase):
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

    def set_recipient_notification_settings(self, global_setting, portal_group_setting):
        settings_obj = GlobalUserNotificationSetting.objects.get_object_for_user(self.recipient)
        settings_obj.portal_group_setting = portal_group_setting
        settings_obj.setting = global_setting
        settings_obj.save()

    def create_events(self):
        NoteFactory(group=self.forum, creator=self.creator)
        NoteFactory(group=self.user_group, creator=self.creator)

    def collect_digest_events(self, digest_setting):
        seen_events = []

        def fake_render(event):
            seen_events.append(event)
            return f'<div>{event.id}</div>'

        with patch(
            'cosinnus_notifications.digest.render_digest_item_for_notification_event',
            side_effect=fake_render,
        ):
            send_digest_for_current_portal(digest_setting, debug_run_for_user=self.recipient)

        return seen_events

    def assert_digest_contains_groups(self, events, expected_groups):
        event_groups = {event.group for event in events}
        self.assertSetEqual(event_groups, set(expected_groups))

    def test_send_digest_weekly_global_weekly_portalgroup_weekly(self):
        self.set_recipient_notification_settings(global_setting=SETTING_WEEKLY, portal_group_setting=SETTING_WEEKLY)
        self.create_events()

        seen_events = self.collect_digest_events(SETTING_WEEKLY)

        self.assert_digest_contains_groups(seen_events, [self.forum, self.user_group])

    def test_send_digest_weekly_global_daily_portalgroup_weekly(self):
        self.set_recipient_notification_settings(global_setting=SETTING_DAILY, portal_group_setting=SETTING_WEEKLY)
        self.create_events()

        seen_events = self.collect_digest_events(SETTING_WEEKLY)

        self.assert_digest_contains_groups(seen_events, [self.forum])

    def test_send_digest_daily_global_daily_portalgroup_weekly(self):
        self.set_recipient_notification_settings(global_setting=SETTING_DAILY, portal_group_setting=SETTING_WEEKLY)
        self.create_events()

        seen_events = self.collect_digest_events(SETTING_DAILY)

        self.assert_digest_contains_groups(seen_events, [self.user_group])

    def test_send_digest_daily_global_never_portalgroup_daily(self):
        self.set_recipient_notification_settings(global_setting=SETTING_NEVER, portal_group_setting=SETTING_DAILY)
        self.create_events()

        seen_events = self.collect_digest_events(SETTING_DAILY)

        self.assert_digest_contains_groups(seen_events, [])
