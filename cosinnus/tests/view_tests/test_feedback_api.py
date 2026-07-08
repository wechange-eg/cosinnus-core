from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase

from cosinnus.models import MEMBERSHIP_ADMIN, CosinnusPortal, CosinnusPortalMembership, CosinnusReportedObject
from cosinnus.models.group_extra import CosinnusSociety
from cosinnus_event.models import Event


class ReportAPITest(APITestCase):
    """Test report API."""

    # test data
    test_admin = None
    test_event = None

    # api urls
    report_api_url = None

    @classmethod
    def setUpTestData(cls):
        # create test user and portal admin
        cls.test_user = get_user_model().objects.create(username=1, email='user@example.com', first_name='LocalUser')
        cls.test_admin = get_user_model().objects.create(username=2, email='admin@example.com', first_name='LocalAdmin')
        CosinnusPortalMembership.objects.create(
            user=cls.test_admin, group=CosinnusPortal.get_current(), status=MEMBERSHIP_ADMIN
        )

        # create test group
        cls.test_group = CosinnusSociety.objects.create(name='GroupSettingsTestGroup')

        # create test event
        cls.test_event = Event.objects.create(title='TestEvent', group=cls.test_group)

        # set urls
        cls.report_api_url = reverse('cosinnus:frontend-api:api-report-event')

    @patch('cosinnus.views.feedback.send_mail_or_fail_threaded')
    def test_report_event(self, mock_send_mail_or_fail_threaded):
        # make sure no report exist
        self.assertFalse(CosinnusReportedObject.objects.exists())

        # login portal admin once, as it is required to receive the report email
        self.client.force_login(self.test_admin)
        self.client.logout()

        repost_post_data = {'object_id': self.test_event.id, 'text': 'TestReport'}

        # anonymous user has no access
        res = self.client.post(self.report_api_url, data=repost_post_data, format='json')
        self.assertEqual(res.status_code, 403)

        # logged-in user can report
        self.assertFalse(CosinnusReportedObject.objects.exists())
        self.client.force_login(self.test_user)
        res = self.client.post(self.report_api_url, data=repost_post_data, format='json')
        self.assertEqual(res.status_code, 200)

        # check report created
        reported_object = CosinnusReportedObject.objects.last()
        self.assertEqual(reported_object.creator, self.test_user)
        self.assertEqual(reported_object.target_object, self.test_event)
        self.assertEqual(reported_object.text, repost_post_data['text'])

        # check email send to portal admin
        self.assertEqual(mock_send_mail_or_fail_threaded.call_count, 1)
        self.assertEqual(mock_send_mail_or_fail_threaded.call_args[0][0], self.test_admin.email)
        self.assertIn('Offensive item reported:', mock_send_mail_or_fail_threaded.call_args[0][1])
        self.assertEqual(
            mock_send_mail_or_fail_threaded.call_args[0][2], 'cosinnus/mail/reported_object_submitted.html'
        )
