from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from cosinnus.models.group import CosinnusPortal
from cosinnus.models.group_extra import CosinnusSociety
from cosinnus.utils.urls import group_aware_reverse

User = get_user_model()


TEST_USER_DATA = {
    'username': '1',
    'email': 'testuser@example.com',
    'first_name': 'Test',
    'last_name': 'User'
}


class MainContentApiViewTest(APITestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.api_url = reverse("cosinnus:frontend-api:api-content-main")
        cls.test_user = User.objects.create(**TEST_USER_DATA)
        cls.group = CosinnusSociety.objects.create(name='Test Group')
        cls.forum_group = CosinnusSociety.objects.create(name='Forum')
        cls.portal = CosinnusPortal.get_current()
        site = cls.portal.site
        site.domain = 'testserver:80'
        site.save()
        cls.portal.protocol = 'http'
        cls.portal.save()
        cls.portal.clear_cache()
        print(f'>> setdomain {cls.portal.site.domain}')
        print(f'>>> portalid {cls.portal.id}')
        cls.domain = cls.portal.get_domain()
        print(f'>> gotdomain {cls.domain}')
        
    @classmethod
    def get_api_url(cls, url_param):
        return cls.api_url + '?url=' + url_param
    
    def test_forum_group_really_forum(self):
        """ Just to make sure settings/DB isn't configured incorrectly """
        self.assertTrue(self.forum_group.is_forum_group)
    
    def test_api_anonymous(self):
        response = self.client.get(self.get_api_url(self.domain))
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['personal'])
    
    def test_regular_group(self):
        self.client.force_login(self.test_user)
        response = self.client.get(self.get_api_url(self.group.get_absolute_url()))
        print(f'>>>> {self.domain}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status_code'], 200) # assertDictEqual
        self.assertEqual(response.data['resolved_url'], self.group.get_absolute_url(), 'URL resolved to requested URL')
        self.assertIn('<div class="x-v3-container">', response.data['content_html'], 'Container html is present')
        self.assertIn('<div class="footer"', response.data['footer_html'], 'Footer html is present')
        self.assertTrue(all([js_item.endswith('.js') for js_item in response.data['js_urls']]),
                        'js_urls only contain .js items')
        self.assertTrue(all([css_item.endswith('.css') for css_item in response.data['css_urls']]),
                    'css_urls only contain .css items')
        self.assertIn('var ', response.data['scripts'], 'scripts response contains some JS')
        self.assertIn('<meta ', response.data['meta'], 'at least one meta item in meta resposne')
        self.assertIn('middle', response.data['sub_navigation'], 'left sidebar navigation is present')
        self.assertGreater(len(response.data['sub_navigation']['middle']), 0,
                           'at least one item in the middle sidebar')
        member_area_url = group_aware_reverse('cosinnus:group-detail', kwargs={'group': self.group})
        self.assertTrue(any([
            link_item['url'] == member_area_url for link_item in response.data['sub_navigation']['bottom']
        ]), 'group member link item in the sidebar bottom navigation')
        self.assertEqual(response.data['main_menu']['icon'], self.group.trans.ICON,
            'main menu button is present and has the default group icon')
        
"""
    @override_settings(COSINNUS_V3_MENU_SPACES_COMMUNITY_ADDITIONAL_LINKS=[('ExternalID', 'External', 'https://example.com/', 'fa-group')])
    def test_community_space_additional_links(self):
        response = self.client.get(self.api_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data['community']['items'][1],
            MenuItem('External', 'https://example.com/', 'fa-group', id='ExternalID')
        )

"""
