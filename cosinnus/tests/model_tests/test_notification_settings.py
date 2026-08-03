from unittest import mock, skip
from unittest.mock import patch

import django
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from cosinnus.api_frontend.serializers.user import CosinnusGlobalUserNotificationSettingSerializer
from cosinnus.conf import settings
from cosinnus.models import CosinnusPortal, GlobalUserNotificationSetting
from cosinnus.tests.factories import ActiveUserFactory
from cosinnus_notifications.views import apply_global_notification_settings

ERROR_MESSAGE = 'Error Message'
User = get_user_model()


def init_notification_settings_for_user(
    user: User, *, setting: int, portal_group_setting: int, rocketchat_setting: int
) -> None:
    """init GlobalUserNotificationSetting for given user since override_settings has no effect on the model defaults"""
    settings_obj: GlobalUserNotificationSetting = user.cosinnus_notification_settings.get()
    settings_obj.setting = setting
    settings_obj.portal_group_setting = portal_group_setting
    settings_obj.rocketchat_setting = rocketchat_setting
    settings_obj.save()


class GlobalUserNotificationSettingsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = ActiveUserFactory()
        init_notification_settings_for_user(cls.user, setting=3, portal_group_setting=0, rocketchat_setting=0)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cache.clear()

    def setUp(self):
        cache.clear()

    def test_unique_for_user_and_portal(self):
        portal = CosinnusPortal.get_current()
        with self.assertRaises(django.db.utils.IntegrityError):
            GlobalUserNotificationSetting.objects.create(user=self.user, portal=portal)

    def test_creation_default_values(self):
        # not using user-object from test-data because we want the portal-configured default-settings
        default_user = ActiveUserFactory()
        notification_setting = GlobalUserNotificationSetting.objects.get_object_for_user(user=default_user)

        with self.subTest(setting='setting'):
            self.assertEqual(notification_setting.setting, settings.COSINNUS_DEFAULT_GLOBAL_NOTIFICATION_SETTING)
        with self.subTest(setting='rocketchat setting'):
            self.assertEqual(
                notification_setting.rocketchat_setting, settings.COSINNUS_DEFAULT_ROCKETCHAT_NOTIFICATION_SETTING
            )

    def test_creation_valid_global_setting(self):
        notification_setting = GlobalUserNotificationSetting.objects.get_object_for_user(user=self.user)
        notification_setting.setting = 1
        notification_setting.save()
        self.assertEqual(notification_setting.setting, 1)

    def test_creation_valid_rocketchat_setting(self):
        notification_setting = GlobalUserNotificationSetting.objects.get_object_for_user(user=self.user)
        notification_setting.rocketchat_setting = 1
        notification_setting.save()
        self.assertEqual(notification_setting.rocketchat_setting, 1)

    @skip('Field validation is not implemented')
    def test_creation_invalid(self): ...

    @patch('cosinnus.models.profile.GlobalUserNotificationSettingManager.clear_cache_for_user')
    def test_save_clears_cache(self, patched_clear_cache_for_user):
        notification_setting = GlobalUserNotificationSetting.objects.get_object_for_user(user=self.user)
        notification_setting.rocketchat_setting = 1
        notification_setting.save()
        patched_clear_cache_for_user.assert_called_once()


class TestGlobalUserSerializer(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = ActiveUserFactory()
        init_notification_settings_for_user(cls.user, setting=3, portal_group_setting=0, rocketchat_setting=0)

    def test_serialize_notification_setting(self):
        notification_setting = GlobalUserNotificationSetting.objects.get_object_for_user(user=self.user)
        serializer = CosinnusGlobalUserNotificationSettingSerializer(notification_setting)

        self.assertEqual(
            serializer.data,
            {
                'setting': 3,
                'portal_group_setting': 0,
            },
        )

    def test_update_notification_setting(self):
        notification_setting = GlobalUserNotificationSetting.objects.get_object_for_user(user=self.user)
        serializer = CosinnusGlobalUserNotificationSettingSerializer(notification_setting)
        serializer.update(notification_setting, {'setting': 4, 'rocketchat_setting': 5})

        self.assertEqual(notification_setting.setting, 4)
        self.assertEqual(notification_setting.rocketchat_setting, 5)


class UserNotificationSettingAPITest(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = ActiveUserFactory()
        init_notification_settings_for_user(cls.user, setting=3, portal_group_setting=0, rocketchat_setting=0)

        cls.url = reverse('cosinnus:frontend-api:api-user-notification-setting')

        if not GlobalUserNotificationSetting.objects.filter(user=cls.user).exists():
            raise AssertionError('GlobalUserNotificationSetting does not exist for user.')

    def test_403_when_not_authenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_notification_setting(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['setting'], 3)
        self.assertEqual(response.data['portal_group_setting'], 0)

    def test_update_notification_setting_valid(self):
        new_settings = {'setting': 2, 'portal_group_setting': 1}

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, data=new_settings, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['portal_group_setting'], new_settings['portal_group_setting'])
        self.assertEqual(response.data['setting'], new_settings['setting'])

        # data has been changed
        notification_setting = GlobalUserNotificationSetting.objects.get_object_for_user(user=self.user)
        self.assertEqual(notification_setting.setting, new_settings['setting'])
        self.assertEqual(notification_setting.portal_group_setting, new_settings['portal_group_setting'])

    def test_update_notification_setting_invalid_value_4(self):
        new_settings = {'setting': 4, 'portal_group_setting': 1}

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, data=new_settings, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # data has not been changed
        notification_setting = GlobalUserNotificationSetting.objects.get_object_for_user(user=self.user)
        self.assertEqual(notification_setting.setting, 3)
        self.assertEqual(notification_setting.portal_group_setting, 0)

    def test_update_notification_setting_partial_global_valid(self):
        new_settings = {'setting': 1}

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, data=new_settings, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['setting'], new_settings['setting'])

        # data has been changed
        notification_setting = GlobalUserNotificationSetting.objects.get_object_for_user(user=self.user)
        self.assertEqual(notification_setting.setting, new_settings['setting'])

    def test_update_notification_setting_partial_portal_group_valid(self):
        new_settings = {'portal_group_setting': 1}

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, data=new_settings, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['portal_group_setting'], new_settings['portal_group_setting'])

        # data has been changed
        notification_setting = GlobalUserNotificationSetting.objects.get_object_for_user(user=self.user)
        self.assertEqual(notification_setting.portal_group_setting, new_settings['portal_group_setting'])

    def test_update_notification_setting_invalid(self):
        new_settings = {'setting': 4, 'portal_group_setting': -1}

        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, data=new_settings, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # data has not been changed
        notification_setting = GlobalUserNotificationSetting.objects.get_object_for_user(user=self.user)
        self.assertEqual(notification_setting.setting, 3)
        self.assertEqual(notification_setting.portal_group_setting, 0)

    @override_settings(COSINNUS_ROCKET_ENABLED=True)
    @patch('cosinnus_message.utils.utils.save_rocketchat_mail_notification_preference_for_user_setting')
    def test_rocketchat_error_on_setting_never_globally(self, mock_save_rc_settings):
        new_settings = {'setting': 0, 'portal_group_setting': 0}

        self.client.force_authenticate(user=self.user)

        original_apply_settings = apply_global_notification_settings

        def apply_settings_and_return_error(*args, **kwargs):
            original_apply_settings(*args, **kwargs)
            return [ERROR_MESSAGE]

        with patch(
            'cosinnus.api_frontend.views.user.apply_global_notification_settings',
            side_effect=apply_settings_and_return_error,
        ):
            response = self.client.post(self.url, data=new_settings, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(response.data['warnings'], [ERROR_MESSAGE])

        # local data has been changed
        notification_setting = GlobalUserNotificationSetting.objects.get_object_for_user(user=self.user)
        self.assertEqual(notification_setting.setting, 0)
        self.assertEqual(notification_setting.portal_group_setting, 0)
        self.assertEqual(notification_setting.rocketchat_setting, 0)


@mock.patch(
    'cosinnus_message.utils.utils.save_rocketchat_mail_notification_preference_for_user_setting',
    return_value=True,
)
class ApplyGlobalNotificationSettingsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = ActiveUserFactory()
        init_notification_settings_for_user(cls.user, setting=3, portal_group_setting=0, rocketchat_setting=0)

        if not GlobalUserNotificationSetting.objects.filter(user=cls.user).exists():
            raise AssertionError('GlobalUserNotificationSetting does not exist for user.')

    def get_setting_obj(self):
        return GlobalUserNotificationSetting.objects.get_object_for_user(self.user)

    @override_settings(COSINNUS_ROCKET_ENABLED=False)
    def test_applies_valid_global_and_portal_group_settings(self, mock_save_rocketchat):
        result = apply_global_notification_settings(
            user=self.user,
            global_setting=GlobalUserNotificationSetting.SETTING_DAILY,
            portal_group_setting=GlobalUserNotificationSetting.SETTING_WEEKLY,
            rocketchat_setting=None,
        )

        self.assertListEqual(result, [])

        setting_obj = self.get_setting_obj()
        self.assertEqual(setting_obj.setting, GlobalUserNotificationSetting.SETTING_DAILY)
        self.assertEqual(
            setting_obj.portal_group_setting,
            GlobalUserNotificationSetting.SETTING_WEEKLY,
        )

    @override_settings(COSINNUS_ROCKET_ENABLED=False)
    def test_none_values_are_ignored(self, mock_save_rocketchat):
        setting_obj = self.get_setting_obj()
        setting_obj.setting = GlobalUserNotificationSetting.SETTING_DAILY
        setting_obj.portal_group_setting = GlobalUserNotificationSetting.SETTING_WEEKLY
        setting_obj.rocketchat_setting = GlobalUserNotificationSetting.ROCKETCHAT_SETTING_MENTIONS
        setting_obj.save()

        result = apply_global_notification_settings(
            user=self.user,
            global_setting=None,
            portal_group_setting=None,
            rocketchat_setting=None,
        )

        self.assertListEqual(result, [])

        setting_obj.refresh_from_db()
        self.assertEqual(setting_obj.setting, GlobalUserNotificationSetting.SETTING_DAILY)
        self.assertEqual(
            setting_obj.portal_group_setting,
            GlobalUserNotificationSetting.SETTING_WEEKLY,
        )
        self.assertEqual(
            setting_obj.rocketchat_setting,
            GlobalUserNotificationSetting.ROCKETCHAT_SETTING_MENTIONS,
        )

    @override_settings(COSINNUS_ROCKET_ENABLED=False)
    def test_zero_value_is_applied_when_valid(self, mock_save_rocketchat):
        setting_obj = self.get_setting_obj()
        setting_obj.setting = GlobalUserNotificationSetting.SETTING_DAILY
        setting_obj.save()

        result = apply_global_notification_settings(
            user=self.user,
            global_setting=GlobalUserNotificationSetting.SETTING_NEVER,
            portal_group_setting=None,
            rocketchat_setting=None,
        )

        self.assertListEqual(result, [])

        setting_obj.refresh_from_db()
        self.assertEqual(setting_obj.setting, GlobalUserNotificationSetting.SETTING_NEVER)

    @override_settings(COSINNUS_ROCKET_ENABLED=False)
    def test_invalid_values_are_ignored(self, mock_save_rocketchat):
        setting_obj = self.get_setting_obj()
        setting_obj.setting = GlobalUserNotificationSetting.SETTING_DAILY
        setting_obj.portal_group_setting = GlobalUserNotificationSetting.SETTING_WEEKLY
        setting_obj.rocketchat_setting = GlobalUserNotificationSetting.ROCKETCHAT_SETTING_MENTIONS
        setting_obj.save()

        result = apply_global_notification_settings(
            user=self.user,
            global_setting=999,
            portal_group_setting=999,
            rocketchat_setting=999,
        )

        self.assertListEqual(result, [])

        setting_obj.refresh_from_db()
        self.assertEqual(setting_obj.setting, GlobalUserNotificationSetting.SETTING_DAILY)
        self.assertEqual(
            setting_obj.portal_group_setting,
            GlobalUserNotificationSetting.SETTING_WEEKLY,
        )
        self.assertEqual(
            setting_obj.rocketchat_setting,
            GlobalUserNotificationSetting.ROCKETCHAT_SETTING_MENTIONS,
        )

    @override_settings(COSINNUS_ROCKET_ENABLED=False)
    def test_rocketchat_is_not_called_when_disabled(self, mock_save_rocketchat):
        result = apply_global_notification_settings(
            user=self.user,
            global_setting=None,
            portal_group_setting=None,
            rocketchat_setting=GlobalUserNotificationSetting.ROCKETCHAT_SETTING_MENTIONS,
        )

        self.assertListEqual(result, [])
        mock_save_rocketchat.assert_not_called()

    @override_settings(COSINNUS_ROCKET_ENABLED=True)
    def test_valid_rocketchat_setting_is_saved_and_propagated(self, mock_save_rocketchat):
        result = apply_global_notification_settings(
            user=self.user,
            global_setting=None,
            portal_group_setting=None,
            rocketchat_setting=GlobalUserNotificationSetting.ROCKETCHAT_SETTING_MENTIONS,
        )

        self.assertListEqual(result, [])

        setting_obj = self.get_setting_obj()
        self.assertEqual(
            setting_obj.rocketchat_setting,
            GlobalUserNotificationSetting.ROCKETCHAT_SETTING_MENTIONS,
        )

        mock_save_rocketchat.assert_called_once_with(
            self.user,
            GlobalUserNotificationSetting.ROCKETCHAT_SETTING_MENTIONS,
        )

    @override_settings(COSINNUS_ROCKET_ENABLED=True)
    def test_global_never_forces_rocketchat_off(self, mock_save_rocketchat):
        mock_save_rocketchat.return_value = True
        result = apply_global_notification_settings(
            user=self.user,
            global_setting=GlobalUserNotificationSetting.SETTING_NEVER,
            portal_group_setting=None,
            rocketchat_setting=GlobalUserNotificationSetting.ROCKETCHAT_SETTING_MENTIONS,
        )

        self.assertListEqual(result, [])

        setting_obj = self.get_setting_obj()
        self.assertEqual(setting_obj.setting, GlobalUserNotificationSetting.SETTING_NEVER)
        self.assertEqual(
            setting_obj.rocketchat_setting,
            GlobalUserNotificationSetting.ROCKETCHAT_SETTING_OFF,
        )

        mock_save_rocketchat.assert_called_once_with(
            self.user,
            GlobalUserNotificationSetting.ROCKETCHAT_SETTING_OFF,
        )

    @override_settings(COSINNUS_ROCKET_ENABLED=True)
    def test_returns_error_if_rocketchat_save_returns_false(self, mock_save_rocketchat):
        mock_save_rocketchat.return_value = False
        result = apply_global_notification_settings(
            user=self.user,
            global_setting=None,
            portal_group_setting=None,
            rocketchat_setting=GlobalUserNotificationSetting.ROCKETCHAT_SETTING_MENTIONS,
        )

        self.assertIsNotNone(result)

        setting_obj = self.get_setting_obj()
        self.assertEqual(
            setting_obj.rocketchat_setting,
            GlobalUserNotificationSetting.ROCKETCHAT_SETTING_MENTIONS,
        )

        mock_save_rocketchat.assert_called_once_with(
            self.user,
            GlobalUserNotificationSetting.ROCKETCHAT_SETTING_MENTIONS,
        )

    @override_settings(COSINNUS_ROCKET_ENABLED=True)
    @mock.patch('logging.exception')
    def test_saves_setting_obj_even_if_rocketchat_save_raises_exception(
        self, mock_logging_exception, mock_save_rocketchat
    ):
        mock_save_rocketchat.side_effect = Exception('boom')
        result = apply_global_notification_settings(
            user=self.user,
            global_setting=GlobalUserNotificationSetting.SETTING_DAILY,
            portal_group_setting=GlobalUserNotificationSetting.SETTING_WEEKLY,
            rocketchat_setting=GlobalUserNotificationSetting.ROCKETCHAT_SETTING_MENTIONS,
        )

        self.assertIsNotNone(result)

        setting_obj = self.get_setting_obj()
        self.assertEqual(setting_obj.setting, GlobalUserNotificationSetting.SETTING_DAILY)
        self.assertEqual(
            setting_obj.portal_group_setting,
            GlobalUserNotificationSetting.SETTING_WEEKLY,
        )
        self.assertEqual(
            setting_obj.rocketchat_setting,
            GlobalUserNotificationSetting.ROCKETCHAT_SETTING_MENTIONS,
        )

        mock_save_rocketchat.assert_called_once_with(
            self.user,
            GlobalUserNotificationSetting.ROCKETCHAT_SETTING_MENTIONS,
        )
        mock_logging_exception.assert_called_once()

    @override_settings(COSINNUS_ROCKET_ENABLED=True)
    def test_invalid_rocketchat_setting_is_ignored_and_not_propagated(self, mock_save_rocketchat):
        setting_obj = self.get_setting_obj()
        setting_obj.rocketchat_setting = GlobalUserNotificationSetting.ROCKETCHAT_SETTING_MENTIONS
        setting_obj.save()

        result = apply_global_notification_settings(
            user=self.user,
            global_setting=None,
            portal_group_setting=None,
            rocketchat_setting=999,
        )

        self.assertListEqual(result, [])

        setting_obj.refresh_from_db()
        self.assertEqual(
            setting_obj.rocketchat_setting,
            GlobalUserNotificationSetting.ROCKETCHAT_SETTING_MENTIONS,
        )

        mock_save_rocketchat.assert_not_called()
