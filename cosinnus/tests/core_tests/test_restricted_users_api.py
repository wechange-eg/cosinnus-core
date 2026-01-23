from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, override_settings

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.managed_tags import CosinnusManagedTag, CosinnusManagedTagAssignment

User = get_user_model()


TEST_USER_UNRESTRICTED_DATA = {
    'username': '1',
    'email': 'unrestricedtestuser@example.com',
    'first_name': 'Regular',
    'last_name': 'TestUser',
}
TEST_USER_RESTRICTED_DATA = {
    'username': '2',
    'email': 'restrictedtestuser@example.com',
    'first_name': 'Restricted',
    'last_name': 'TestUser',
}
RESTRICTED_TAG_SLUG = 'restricted'
RESTRICTED_URL = '/search/'


# override V3 settings so V3 redirects do not confound us
@override_settings(
    COSINNUS_V3_FRONTEND_ENABLED=False,
    COSINNUS_V3_FRONTEND_EVERYWHERE_ENABLED=False,
    COSINNUS_MANAGED_TAGS_ENABLED=True,
    COSINNUS_MANAGED_TAGS_ASSIGN_MULTIPLE_ENABLED=True,
    MIDDLEWARE=settings.MIDDLEWARE
    + [
        'cosinnus.core.middleware.cosinnus_middleware.ManagedTagBlockURLsMiddleware',
    ],
)
class RestrictedUsersTest(APITestCase):
    """A collection of tests focussing on several conf settings that restrict user interactions and permissions
    based on users having a configured managed tag assigned.
    This test suite performs negative-tests as well, to make sure these restrictions don't leak over when the same tag
    is assigned, but the settings are not configured for this portal. This uses the `should_be_restricted` arg."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.map_url = reverse('cosinnus:map')
        cls.portal = CosinnusPortal.get_current()
        cls.test_user_unrestricted = User.objects.create(**TEST_USER_UNRESTRICTED_DATA)
        cls.test_user_restricted = User.objects.create(**TEST_USER_RESTRICTED_DATA)
        cls.restricted_tag = CosinnusManagedTag.objects.create(
            portal=cls.portal, slug=RESTRICTED_TAG_SLUG, name='Restricted'
        )
        CosinnusManagedTagAssignment.assign_managed_tag_to_object(
            cls.test_user_restricted.cosinnus_profile, cls.restricted_tag.slug
        )

    def test_testsetup_restriced_tag_assignment(self):
        """Preflight tests if the test setup is correct"""
        slugs = self.test_user_restricted.cosinnus_profile.get_managed_tag_slugs()
        self.assertListEqual(slugs, [RESTRICTED_TAG_SLUG], 'the restricted user is assigned the restricted tag')
        slugs = self.test_user_unrestricted.cosinnus_profile.get_managed_tag_slugs()
        self.assertListEqual(slugs, [], 'the unrestricted user is assigned no tag')

    def _blocked_url_test(self, should_be_restricted=True):
        """Tests restricted URLs access for restricted and non-restricted users"""
        # restricted users can't access some restriced sites
        self.client.force_login(self.test_user_restricted)
        response = self.client.get(RESTRICTED_URL)
        self.assertEqual(
            response.status_code == 403,
            should_be_restricted,
            f'Restricted view ({response.status_code}) is restricted for a restricted user'
            + (' (NEGATIVE)' if not should_be_restricted else ''),
        )
        response = self.client.get(self.map_url)
        self.assertEqual(
            response.status_code,
            200,
            f'Normal view ({response.status_code}) is fine for a restricted user'
            + (' (NEGATIVE)' if not should_be_restricted else ''),
        )

        # but regular users can access them
        self.client.logout()
        self.client.force_login(self.test_user_unrestricted)
        response = self.client.get(RESTRICTED_URL)
        self.assertEqual(
            response.status_code == 403,
            False,
            f'Restricted view ({response.status_code}) is fine for a normal user'
            + (' (NEGATIVE)' if not should_be_restricted else ''),
        )
        response = self.client.get(self.map_url)
        self.assertEqual(
            response.status_code,
            200,
            f'Normal view ({response.status_code}) is fine for a normal user'
            + (' (NEGATIVE)' if not should_be_restricted else ''),
        )

    @override_settings(
        COSINNUS_MANAGED_TAGS_RESTRICT_URLS_BLOCKED={
            RESTRICTED_TAG_SLUG: [
                f'^{RESTRICTED_URL}',
            ]
        }
    )
    def test_blocked_urls(self):
        self._blocked_url_test()

    @override_settings(COSINNUS_MANAGED_TAGS_RESTRICT_URLS_BLOCKED={})
    def test_blocked_urls_negative(self):
        self._blocked_url_test(should_be_restricted=False)
