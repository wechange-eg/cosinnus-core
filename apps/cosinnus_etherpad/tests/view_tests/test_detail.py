# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from builtins import str
from django.conf import settings
from django.urls import reverse

from cosinnus_etherpad.models import Etherpad
from tests.view_tests.base import ViewTestCase


class DetailTest(ViewTestCase):

    def test_detail(self):
        """
        Should return 200, contain pad title and cookie for etherpad server
        session
        """
        pad = Etherpad.objects.create(group=self.group, title='testpad')
        kwargs = {'group': self.group.slug, 'slug': pad.slug}
        url = reverse('cosinnus:etherpad:pad-detail', kwargs=kwargs)
        client_kwargs = {'SERVER_NAME': 'localhost.sinnwerkstatt.com'}
        response = self.client.get(url, **client_kwargs)

        # should return 200
        self.assertEqual(response.status_code, 200)

        # content should contain pad title
        self.assertIn(pad.title, str(response.content))

        # should set cookie for etherpad server session
        self.assertIn('sessionID', response.cookies)
        # cookie domain should be part of etherpad base url
        self.assertIn(
            response.cookies['sessionID']['domain'],
            settings.COSINNUS_ETHERPAD_BASE_URL)

        # be nice to remote server and delete pad also there
        pad.delete()
