from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase, override_settings

from cosinnus.models import UserBlock
from cosinnus.utils.permissions import check_user_blocks_user, filter_blocks_for_user

User = get_user_model()


@override_settings(COSINNUS_ENABLE_USER_BLOCK=True)
class UserBlockTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user_main = User.objects.create(username='main_user')
        cls.user_blocked_by_main = User.objects.create(username='blocked_by_main')
        cls.user_blocking_main = User.objects.create(username='blocking_main')
        cls.user_neutral = User.objects.create(username='neutral_user')
        cls.user_anonymous = AnonymousUser()

        # main user blocks other user
        UserBlock.objects.create(user=cls.user_main, blocked_user=cls.user_blocked_by_main)
        # main user us blocked by other user
        UserBlock.objects.create(user=cls.user_blocking_main, blocked_user=cls.user_main)

    @override_settings(COSINNUS_ENABLE_USER_BLOCK=False)
    def test_filter_blocks_nop_if_blocking_disabled(self):
        all_users = User.objects.all()

        # given queryset is returned
        filtered_qs = filter_blocks_for_user(self.user_main, all_users)
        self.assertEqual(filtered_qs, all_users)

    def test_filter_blocks_for_user_removes_both_ways(self):
        all_users = User.objects.all()
        filtered_qs = filter_blocks_for_user(self.user_main, all_users)

        # only main user and neutral user remain
        self.assertEqual(filtered_qs.count(), 2)
        self.assertIn(self.user_main, filtered_qs)
        self.assertIn(self.user_neutral, filtered_qs)

    def test_filter_blocks_nop_for_anonymous_user(self):
        all_users = User.objects.all()

        # given queryset is returned
        filtered_qs = filter_blocks_for_user(self.user_anonymous, all_users)
        self.assertEqual(filtered_qs, all_users)

    def test_filter_blocks_for_user_with_empty_queryset(self):
        empty_qs = User.objects.none()
        filtered_qs = filter_blocks_for_user(self.user_main, empty_qs)

        self.assertEqual(filtered_qs.count(), 0)

    def test_check_user_blocks_user_is_true(self):
        result = check_user_blocks_user(self.user_main, self.user_blocked_by_main)
        self.assertTrue(result)

    def test_check_user_blocks_user_is_false_for_neutral(self):
        result = check_user_blocks_user(self.user_main, self.user_neutral)
        self.assertFalse(result)

    @override_settings(COSINNUS_ENABLE_USER_BLOCK=False)
    def test_check_user_blocks_user_returns_false_if_feature_disabled(self):
        # returns False despite an existing block
        result = check_user_blocks_user(self.user_main, self.user_blocked_by_main)
        self.assertFalse(result)

    def test_check_user_blocks_user_unsaved_users(self):
        unsaved_user = User(username='unsaved')

        # returns False for unsaved user
        result = check_user_blocks_user(self.user_main, unsaved_user)
        self.assertFalse(result)

    def test_check_user_blocks_user_anonymous(self):
        # returns False for unsaved user
        result = check_user_blocks_user(self.user_main, self.user_anonymous)
        self.assertFalse(result)
