import re

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APILiveServerTestCase

from cosinnus.conf import settings
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import CosinnusSociety
from cosinnus.models.membership import MEMBERSHIP_MEMBER
from cosinnus.utils.urls import group_aware_reverse

User = get_user_model()

TEST_USER_DATA = {'username': '1', 'email': 'testuser@example.com', 'first_name': 'Test', 'last_name': 'User'}


class MainContentViewTest(APILiveServerTestCase):
    # Not sure why, but setting available apps to installed apps fixes the database setup.
    # Without this the test database setup fails unable to create wagtail tables.
    available_apps = settings.INSTALLED_APPS

    @classmethod
    def setUpClass(cls):
        cache.clear()
        super().setUpClass()
        cls.api_url = reverse('cosinnus:frontend-api:api-content-main')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cache.clear()

    def setUp(self):
        cache.clear()
        super().setUp()
        site = Site.objects.first()
        site.domain = f'{self.host}:{self.server_thread.port}'
        site.save()
        self.domain = f'http://{site.domain}'
        # recreate portal, as objects created by migrations are droped by the TransactionTestCase teardown.
        CosinnusPortal.objects.get_or_create(
            id=1, defaults={'name': 'default portal', 'slug': 'default', 'public': True, 'site': site}
        )
        self.test_user = User.objects.create(**TEST_USER_DATA)
        self.test_user_profile = self.test_user.cosinnus_profile
        self.test_group = CosinnusSociety.objects.create(name='Test Group')
        self.test_group.memberships.create(user=self.test_user, status=MEMBERSHIP_MEMBER)

    def test_group_detail(self):
        """Basic test for accessing the group dashboard."""
        self.client.force_login(self.test_user)
        content_url = f'/group/{self.test_group.slug}/'
        response = self.client.get(self.api_url + f'?url={content_url}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status_code'], 200)
        self.assertEqual(response.data['resolved_url'], content_url)
        self.assertIsNotNone(re.search(rf'<h2>\s*{self.test_group.name}\s*</h2>', response.data['content_html']))
        self.assertIn('<div class="x-v3-container', response.data['content_html'], 'Container html is present')
        self.assertIn('<div class="footer"', response.data['footer_html'], 'Footer html is present')
        self.assertTrue(
            all([re.match('^.*\.js(\?.*)?$', js_item) for js_item in response.data['js_urls']]),
            'js_urls only contain .js items',
        )
        self.assertTrue(
            all([css_item.endswith('.css') for css_item in response.data['css_urls']]),
            'css_urls only contain .css items',
        )
        self.assertIn('var ', response.data['scripts'], 'scripts response contains some JS')
        self.assertIn('<meta ', response.data['meta'], 'at least one meta item in meta resposne')
        self.assertIn('middle', response.data['sub_navigation'], 'left sidebar navigation is present')
        self.assertEqual(response.data['sub_navigation']['top'][0]['label'], 'Microsite')
        self.assertGreater(len(response.data['sub_navigation']['middle']), 0, 'at least one item in the middle sidebar')
        member_area_url = group_aware_reverse(
            'cosinnus:group-detail', kwargs={'group': self.test_group}, skip_domain=True
        )
        self.assertTrue(
            any([link_item['url'] == member_area_url for link_item in response.data['sub_navigation']['top']]),
            'group member link item in the sidebar top navigation',
        )
        self.assertEqual(response.data['main_menu']['label'], self.test_group.name)
        self.assertEqual(
            response.data['main_menu']['icon'],
            self.test_group.trans.ICON,
            'main menu button is present and has the default group icon',
        )

    def test_personal_dashboard(self):
        """Basic test for accessing the personal dashboard."""
        self.client.force_login(self.test_user)
        content_url = '/dashboard/'
        response = self.client.get(self.api_url + f'?url={content_url}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status_code'], 200)
        self.assertEqual(response.data['resolved_url'], content_url)
        self.assertIn('<h2 class="headline mobile-hidden">News</h2>', response.data['content_html'])
        self.assertIn('<div class="x-v3-container', response.data['content_html'], 'Container html is present')
        self.assertIn('<div class="footer"', response.data['footer_html'], 'Footer html is present')
        self.assertTrue(
            all([re.match('^.*\.js(\?.*)?$', js_item) for js_item in response.data['js_urls']]),
            'js_urls only contain .js items',
        )
        self.assertTrue(
            all([css_item.endswith('.css') for css_item in response.data['css_urls']]),
            'css_urls only contain .css items',
        )
        self.assertIn('var ', response.data['scripts'], 'scripts response contains some JS')
        self.assertIn('<meta ', response.data['meta'], 'at least one meta item in meta resposne')
        self.assertEqual(response.data['sub_navigation'], None, 'no subnavigation in dashboard')
        self.assertEqual(response.data['main_menu']['label'], 'Personal Dashboard')
        self.assertEqual(
            response.data['main_menu']['icon'], 'fa-user', 'main menu button is present and has the user ico'
        )
