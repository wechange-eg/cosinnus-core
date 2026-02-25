import datetime
import html
import re
from dataclasses import dataclass
from typing import List, Optional
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.template.defaultfilters import date as django_date
from django.test import TestCase, override_settings
from django.utils import translation
from freezegun import freeze_time

from cosinnus.cron import SendGroupPremiumExpirationWarningEmails, SwitchGroupPremiumFeatures
from cosinnus.models import MEMBERSHIP_ADMIN
from cosinnus.models.group import CosinnusBaseGroup, CosinnusGroupMembership
from cosinnus.models.group_extra import CosinnusProject, CosinnusSociety

User = get_user_model()


def html_normalize_text(html_content: str) -> str:
    unescaped = html.unescape(html_content)
    normalized = re.sub(r'\s+', ' ', unescaped)
    return normalized


def _set_group_state(group: CosinnusBaseGroup, premium_until, expired_on):
    group.enable_user_premium_choices_until = premium_until
    if expired_on:
        group.settings['premium_features_expired_on'] = expired_on
    group.save()
    group.refresh_from_db()


class TestDataMixin:
    # noinspection PyPep8Naming,PyUnresolvedReferences
    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(username='1', email='testuser@example.com', first_name='Test', last_name='User')
        user.last_login = datetime.date.today()
        user.cosinnus_profile.tos_accepted = True
        user.cosinnus_profile.language = 'en'
        user.cosinnus_profile.save()
        user.save()
        cls.user = user
        cls.group: CosinnusBaseGroup = CosinnusSociety.objects.create(name='testgroup')
        cls.project: CosinnusBaseGroup = CosinnusProject.objects.create(name='testproject')
        CosinnusGroupMembership.objects.create(user=cls.user, group=cls.group, status=MEMBERSHIP_ADMIN)
        CosinnusGroupMembership.objects.create(user=cls.user, group=cls.project, status=MEMBERSHIP_ADMIN)


@override_settings(
    COSINNUS_V3_FRONTEND_EVERYWHERE_ENABLED=False,
    COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS_ADMIN_RESTRICTED=True,
    COSINNUS_BBB_GROUP_PREMIUM_WARNING_DAYS=7,
)
class GroupPremiumBBBInfoBoxTest(TestDataMixin, TestCase):
    # Message strings to test for, can be multiple per state.
    MESSAGES = {
        CosinnusBaseGroup.GROUP_PREMIUM_STATE_NONE: (),
        CosinnusBaseGroup.GROUP_PREMIUM_STATE_ACTIVE_FAR: (
            'This {type} currently has Videoconference Pro booked until Feb. 20, 2026',
        ),
        CosinnusBaseGroup.GROUP_PREMIUM_STATE_ACTIVE_ENDS_SOON: (
            'The booking for Videoconference Pro for this {type} ends after Feb. 5, 2026',
            '5 days',
        ),
        CosinnusBaseGroup.GROUP_PREMIUM_STATE_EXPIRED: (
            'The booking for Videoconference Pro for this {type} ended on Jan. 15, 2026',
        ),
    }

    def setUp(self):
        self.client.force_login(self.user)
        translation.activate(None)

    def tearDown(self):
        translation.deactivate()

    def _test_scenario(self, state, current_date, premium_until, expired_on):
        """
        Helper function to test a scenario for both, group and project.
        """
        for obj in [self.group, self.project]:
            label = 'group' if obj.group_is_group else 'project'
            with self.subTest(group_type=label), freeze_time(current_date):
                _set_group_state(obj, premium_until, expired_on)

                with self.subTest(phase='model_state'):
                    self.assertEqual(obj.group_premium_state, state)

                with self.subTest(phase='render_output'):
                    response = self.client.get(obj.get_edit_url())
                    # we could also test for the alert-class warning vs success via BS4
                    html_normalized = html_normalize_text(response.content.decode('utf-8'))
                    for key, templates in self.MESSAGES.items():
                        expected_texts = [template.replace('{type}', label) for template in templates]
                        if key == state:
                            for message in expected_texts:
                                self.assertTrue(
                                    message in html_normalized, f'Expected string "{message}" not present in output.'
                                )
                        else:
                            for message in expected_texts:
                                self.assertFalse(
                                    message in html_normalized, f'Unexpected string "{message}" present in output.'
                                )

    def test_scenario_active(self):
        self._test_scenario(CosinnusBaseGroup.GROUP_PREMIUM_STATE_ACTIVE_FAR, '2026-02-01', '2026-02-20', None)

    def test_scenario_expires_soon(self):
        self._test_scenario(CosinnusBaseGroup.GROUP_PREMIUM_STATE_ACTIVE_ENDS_SOON, '2026-02-01', '2026-02-05', None)

    def test_scenario_expired(self):
        self._test_scenario(CosinnusBaseGroup.GROUP_PREMIUM_STATE_EXPIRED, '2026-02-01', None, '2026-01-15')

    @override_settings(COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS_ADMIN_RESTRICTED=False)
    def test_scenario_active_restricted_false(self):
        self._test_scenario(CosinnusBaseGroup.GROUP_PREMIUM_STATE_NONE, '2026-02-01', '2026-02-20', None)


@dataclass
class SendHtmlMailCallArgs:
    user: User
    subject: str
    content_fragment: str
    topic: Optional[str]


@override_settings(
    COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS_ADMIN_RESTRICTED=True, COSINNUS_BBB_GROUP_PREMIUM_WARNING_DAYS=7
)
class GroupPremiumStateChangeTest(TestDataMixin, TestCase):
    def _execute_scenario(
        self,
        current_date: str,
        premium_until: Optional[str],
        fixture_bbb_active: bool,
        expected_can_have_bbb: bool,
        expected_bbb_active: bool,
        expected_last_warned_for: Optional[str],
        expected_premium_until: Optional[str],
        expected_expired_on: Optional[str],
        expected_mails: List[SendHtmlMailCallArgs],
    ):
        expected_mail_count = len(expected_mails)
        with freeze_time(current_date), patch('cosinnus.core.mail.send_html_mail') as mock_send:
            # set state
            # TODO test this for project also
            self.group.enable_user_premium_choices_until = premium_until
            if fixture_bbb_active:
                self.group.video_conference_type = CosinnusBaseGroup.BBB_MEETING
            self.group.save()

            # do the tasks
            SwitchGroupPremiumFeatures().do()
            SendGroupPremiumExpirationWarningEmails().do()
            self.group.refresh_from_db()

            # assertions
            with self.subTest('bbb available', can_have_bbb_after=expected_can_have_bbb):
                self.assertEqual(self.group.group_can_be_bbb_enabled, expected_can_have_bbb)

            with self.subTest('video conference type', bbb_active=expected_bbb_active):
                if expected_bbb_active:
                    self.assertTrue(self.group.video_conference_type == CosinnusBaseGroup.BBB_MEETING)
                else:
                    self.assertTrue(self.group.video_conference_type == CosinnusBaseGroup.NO_VIDEO_CONFERENCE)

            with self.subTest('valid until', expected_premium_until=expected_premium_until):
                try:
                    premium_until = self.group.enable_user_premium_choices_until.isoformat()
                except AttributeError:
                    premium_until = None
                self.assertEqual(premium_until, expected_premium_until)

            with self.subTest('expired_on', expected_expired_on=expected_expired_on):
                try:
                    expired_on = self.group.group_premium_expired_on.isoformat()
                except AttributeError:
                    expired_on = None
                self.assertEqual(expired_on, expected_expired_on)

            with self.subTest('warning mail sent', expected_mail_count=expected_mail_count):
                self.assertEqual(expected_mail_count, mock_send.call_count)

            for mail in expected_mails:
                with self.subTest('mail content'):
                    args = mock_send.call_args
                    user_arg = args[0][0]
                    subject_arg = args[0][1]
                    content_arg = args[0][2]
                    topic_arg = args[1].get('topic_instead_of_subject')

                    self.assertEqual(user_arg, mail.user)
                    self.assertEqual(subject_arg, mail.subject)
                    self.assertIn(mail.content_fragment, content_arg)
                    self.assertEqual(topic_arg, mail.topic)

            with self.subTest('warning mail marker set', expected_last_warned_for=expected_last_warned_for):
                self.assertEqual(
                    expected_last_warned_for, self.group.settings.get('last_warned_for_premium_choices_until')
                )

    def _get_mail_args_expiration(self) -> SendHtmlMailCallArgs:
        return SendHtmlMailCallArgs(
            user=self.user,
            subject='The booking for Videoconference Pro for the group "testgroup" has ended.',
            content_fragment=f'href="{self.group.get_absolute_url()}"',
            topic=None,
        )

    def _get_mail_args_warning(self, date_until: str, days_left: int) -> SendHtmlMailCallArgs:
        # noinspection PyUnresolvedReferences
        date_str = django_date(datetime.date.fromisoformat(date_until))
        return SendHtmlMailCallArgs(
            user=self.user,
            subject=(
                'The booking for Videoconference Pro for the group "testgroup"'
                f' ends after {date_str} ({days_left} days).'
            ),
            content_fragment=f'href="{self.group.get_absolute_url()}"',
            topic=None,
        )

    def test_active_no_action_needed(self):
        self._execute_scenario(
            '2026-02-01',
            '2026-02-20',
            fixture_bbb_active=True,
            expected_can_have_bbb=True,
            expected_bbb_active=True,
            expected_premium_until='2026-02-20',
            expected_expired_on=None,
            expected_mails=[],
            expected_last_warned_for=None,
        )

    def test_active_warning_triggered(self):
        with self.subTest(phase='initial warning mail'):
            self._execute_scenario(
                '2026-02-01',
                '2026-02-05',
                fixture_bbb_active=True,
                expected_can_have_bbb=True,
                expected_bbb_active=True,
                expected_premium_until='2026-02-05',
                expected_expired_on=None,
                expected_mails=[self._get_mail_args_warning('2026-02-05', 5)],
                expected_last_warned_for='2026-02-05',
            )

        with self.subTest(phase='idempotence check'):
            self._execute_scenario(
                '2026-02-01',
                '2026-02-05',
                fixture_bbb_active=True,
                expected_can_have_bbb=True,
                expected_bbb_active=True,
                expected_premium_until='2026-02-05',
                expected_expired_on=None,
                expected_mails=[],
                expected_last_warned_for='2026-02-05',
            )

        with self.subTest(phase='premium_until_changed'):
            self._execute_scenario(
                '2026-02-01',
                '2026-02-06',
                fixture_bbb_active=True,
                expected_can_have_bbb=True,
                expected_bbb_active=True,
                expected_premium_until='2026-02-06',
                expected_expired_on=None,
                expected_mails=[self._get_mail_args_warning('2026-02-06', 6)],
                expected_last_warned_for='2026-02-06',
            )

    def test_deactivation_triggered(self):
        self._execute_scenario(
            '2026-02-01',
            '2026-01-31',
            fixture_bbb_active=True,
            expected_can_have_bbb=False,
            expected_bbb_active=False,
            expected_premium_until=None,
            expected_expired_on='2026-02-01',
            expected_mails=[self._get_mail_args_expiration()],
            expected_last_warned_for=None,
        )

    def test_expired_no_action_needed(self):
        self._execute_scenario(
            '2026-02-01',
            None,
            fixture_bbb_active=False,
            expected_can_have_bbb=False,
            expected_bbb_active=False,
            expected_premium_until=None,
            expected_expired_on=None,
            expected_mails=[],
            expected_last_warned_for=None,
        )

    @override_settings(COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS_ADMIN_RESTRICTED=False)
    def test_feature_disabled_no_deactivation_triggered(self):
        self._execute_scenario(
            '2026-02-01',
            '2026-01-31',
            fixture_bbb_active=True,
            expected_can_have_bbb=True,
            expected_bbb_active=True,
            expected_premium_until='2026-01-31',
            expected_expired_on=None,
            expected_mails=[],
            expected_last_warned_for=None,
        )

    @override_settings(COSINNUS_BBB_ENABLE_GROUP_AND_EVENT_BBB_ROOMS_ADMIN_RESTRICTED=False)
    def test_feature_disabled_no_warning_sent(self):
        self._execute_scenario(
            '2026-02-01',
            '2026-02-05',
            fixture_bbb_active=True,
            expected_can_have_bbb=True,
            expected_bbb_active=True,
            expected_premium_until='2026-02-05',
            expected_expired_on=None,
            expected_mails=[],
            expected_last_warned_for=None,
        )
