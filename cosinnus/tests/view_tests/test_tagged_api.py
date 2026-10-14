from django.urls import reverse
from rest_framework.test import APITestCase

from cosinnus.conf import settings
from cosinnus.tests.factories import ActiveUserFactory


class GeocodeAPITest(APITestCase):
    """Test geocode API."""

    @classmethod
    def setUpTestData(cls):
        cls.user = ActiveUserFactory()
        cls.api_url = reverse('cosinnus:frontend-api:api-geocode')

    def test_permissions(self):
        res = self.client.get(self.api_url)
        self.assertEqual(res.status_code, 403)
        self.client.force_login(self.user)
        res = self.client.get(self.api_url)
        self.assertEqual(res.status_code, 200)

    def test_api(self):
        self.client.force_login(self.user)
        # request without query returns empty list
        data = self.client.get(self.api_url).json()['data']
        self.assertEqual(data, [])

        # request with query length lower than 3 return empty list
        url = f'{self.api_url}?query=Be'
        data = self.client.get(url).json()['data']
        self.assertEqual(data, [])

        # request with 3 char query returns the result mocked in monkey_patch_geocode_opencage_api.
        url = f'{self.api_url}?query=Ber'
        data = self.client.get(url).json()['data']
        self.assertEqual(
            data,
            [
                {
                    'location': settings.TEST_GEOCODE_MOCKED_ADDRESS,
                    'location_lat': settings.TEST_GEOCODE_MOCKED_LAT,
                    'location_lon': settings.TEST_GEOCODE_MOCKED_LON,
                }
            ],
        )
