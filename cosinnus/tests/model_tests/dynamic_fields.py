# -*- coding: utf-8 -*-

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from cosinnus.dynamic_fields import dynamic_fields

_USERPROFILE_DYNAMIC_UNIQUE_TEST_SETTING = {
    # note: this field is constrained to be unique!
    'unique_testfield': dynamic_fields.CosinnusDynamicField(
        type=dynamic_fields.DYNAMIC_FIELD_TYPE_TEXT_SLUG,
        label='unique testfield',
        unique=True,
        required=False,
    ),
}


class DynamicFieldsUnitTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        pass

    def _create_user(self, username):
        existing_user = get_user_model().objects.filter(username=username).first()
        if existing_user:
            existing_user.delete()
        return get_user_model().objects.create(
            username=username,
            email='%s@mail.com' % username,
            first_name='User %s' % username,
            is_active=True,
        )

    def _set_unique_field(self, user, value):
        """For `test_dynamic_field_unique_check`, sets the value of the user's unique dynamic field"""
        user.cosinnus_profile.dynamic_fields['unique_testfield'] = value

    @override_settings(COSINNUS_USERPROFILE_EXTRA_FIELDS=_USERPROFILE_DYNAMIC_UNIQUE_TEST_SETTING)
    def test_dynamic_field_unique_check(self):
        """Tests the validation of dynamic fields with unique constraints"""
        user_a = self._create_user(username='user_a')
        user_b = self._create_user(username='user_b')

        try:
            self._set_unique_field(user_a, 'val1')
            user_a.cosinnus_profile.save()
            self._set_unique_field(user_b, 'val2')
            user_b.cosinnus_profile.save()
        except ValidationError:
            self.fail('Non-clashing unique fields can be saved')

        try:
            self._set_unique_field(user_a, 'val1')
            user_a.cosinnus_profile.save()
            self._set_unique_field(user_a, 'val1')
            user_a.cosinnus_profile.save()
        except ValidationError:
            self.fail("A unique field doesn't clash with its own instance on repeat saves")

        try:
            self._set_unique_field(user_a, '')
            user_a.cosinnus_profile.save()
            self._set_unique_field(user_b, '')
            user_b.cosinnus_profile.save()
        except ValidationError:
            self.fail('Two empty values do not clash the unique constriant')

        self._set_unique_field(user_a, 'clashing_val')
        user_a.cosinnus_profile.save()
        with self.assertRaises(ValidationError):
            # , 'The unique check properly triggers on clash'
            self._set_unique_field(user_b, 'clashing_val')
            user_b.cosinnus_profile.save()
