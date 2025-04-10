import re
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APILiveServerTestCase

from cosinnus.conf import settings
from cosinnus.core.middleware.frontend_middleware import FrontendMiddleware
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import CosinnusSociety
from cosinnus.models.membership import MEMBERSHIP_MEMBER
from cosinnus.tests.view_tests.views import MainContentFormTestView
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

    def test_template_processing(self):
        """
        Basic test for html processing using the dedicated test template
        cosinnus/templates/cosinnus/tests/main_content_test.html
        """
        content_url = reverse('cosinnus:main-content-test')
        response = self.client.get(self.api_url + f'?url={content_url}')
        self.assertEqual(response.status_code, 200)

        # check response status
        self.assertEqual(response.data['status_code'], 200)
        self.assertEqual(response.data['resolved_url'], content_url)
        self.assertFalse(response.data['redirect'])

        # check meta
        self.assertEqual(response.data['meta'], '<meta charset="utf-8"/>')

        # check js
        self.assertEqual(response.data['js_vendor_urls'], [f'{self.domain}/static/js/vendor/test.js'])
        self.assertEqual(response.data['js_urls'], [f'{self.domain}/static/js/cosinnus.js'])
        self.assertEqual(response.data['script_constants'], 'var constant;')
        self.assertEqual(response.data['scripts'], 'var head_script;\nvar body_script;')

        # check css
        self.assertEqual(response.data['css_urls'], [f'{self.domain}/static/css/test.css'])
        self.assertEqual(response.data['styles'], '.test_style {}')

        # check html content
        self.assertEqual(
            response.data['content_html'].replace('\n', ''), '<div class="x-v3-content"> Test-Content  </div>'
        )

        # check footer
        self.assertEqual(response.data['footer_html'], 'Test-Footer')

        # check subnavigation
        self.assertEqual(response.data['sub_navigation']['top'], [])
        self.assertEqual(response.data['sub_navigation']['bottom'], [])
        self.assertEqual(len(response.data['sub_navigation']['middle']), 2)

        # check leftnav appsmenu link
        sub_navigation1 = response.data['sub_navigation']['middle'][0]
        self.assertIn('Sidebar-', sub_navigation1['id'])
        self.assertEqual(sub_navigation1['label'], 'Appsmenu Link')
        self.assertEqual(sub_navigation1['url'], '/appsmenu-link/')
        self.assertEqual(sub_navigation1['icon'], 'icon1')
        self.assertFalse(sub_navigation1['selected'])

        # check leftnav button
        sub_navigation2 = response.data['sub_navigation']['middle'][1]
        self.assertIn('Sidebar-', sub_navigation2['id'])
        self.assertEqual(sub_navigation2['label'], 'Leftnav Button')
        self.assertEqual(sub_navigation2['url'], '/leftnav-button-link/')
        self.assertEqual(sub_navigation2['icon'], 'icon2')
        self.assertTrue(sub_navigation2['selected'])

        # check main_menu
        self.assertEqual(response.data['main_menu'], {'label': 'Go To...', 'icon': 'fa-arrow-right', 'image': None})

    def test_form_processing(self):
        """Basic tests for main content form processing using a dedicated test form view with a required field."""
        form_url = reverse('cosinnus:main-content-form-test')
        response = self.client.get(self.api_url + f'?url={form_url}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            '<input id="id_test_field" name="test_field" required="" type="text"/>', response.data['content_html']
        )

        # post invalid data redirects to cached form response with the form errors
        data = urlencode({'test_field': ''})
        response = self.client.post(form_url, data, content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 302)
        redirect_url = response.url
        self.assertIn(form_url, redirect_url)
        self.assertIn(FrontendMiddleware.cached_content_key, redirect_url)
        encoded_url_param = urlencode({'url': redirect_url})
        response = self.client.get(self.api_url + f'?{encoded_url_param}')
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            '<ul class="errorlist"><li>test_field<ul class="errorlist"><li>This field is required.</li></ul></li></ul>',
            response.data['content_html'],
        )

        # post valid data redirects to the success url of the form test view
        data = urlencode({'test_field': 'test'})
        response = self.client.post(form_url, data, content_type='application/x-www-form-urlencoded')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, MainContentFormTestView.success_url)
