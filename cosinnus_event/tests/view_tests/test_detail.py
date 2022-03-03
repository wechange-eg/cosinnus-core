# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse
from django.utils.encoding import force_text
from django.utils.timezone import now

from cosinnus_event.models import Event
from tests.view_tests.base import ViewTestCase


class DetailTest(ViewTestCase):

    def test_detail(self):
        """
        Should return 200 and contain event title
        """
        event = Event.objects.create(
            group=self.group,
            creator=self.admin,
            public=True,
            title='testevent',
            from_date=now(),
            to_date=now(),
            state=Event.STATE_SCHEDULED)
        kwargs = {'group': self.group.slug, 'slug': event.slug}
        url = reverse('cosinnus:event:entry-detail', kwargs=kwargs)
        response = self.client.get(url)

        # should return 200
        self.assertEqual(response.status_code, 200)

        # content should contain event title
        self.assertIn(event.title, force_text(response.content))
