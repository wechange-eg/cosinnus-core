# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse
from django.utils.timezone import now

from cosinnus_event.models import Event
from tests.view_tests.base import ViewTestCase


class EditTest(ViewTestCase):

    def setUp(self, *args, **kwargs):
        super(EditTest, self).setUp(*args, **kwargs)
        self.event = Event.objects.create(
            group=self.group,
            creator=self.admin,
            public=True,
            title='testevent',
            from_date=now(),
            to_date=now(),
            state=Event.STATE_SCHEDULED)
        self.kwargs = {'group': self.group.slug, 'slug': self.event.slug}
        self.url = reverse('cosinnus:event:entry-edit', kwargs=self.kwargs)

    def test_get_not_logged_in(self):
        """
        Should return 403 on GET if not logged in
        """
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 403)

    def test_get_logged_in(self):
        """
        Should return 200 on GET and have event title set to readonly in form
        when logged in
        """
        self.client.login(username=self.credential, password=self.credential)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_post_not_logged_in(self):
        """
        Should return 403 on POST if not logged in
        """
        self.client.logout()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 403)

    def test_post_logged_in(self):
        """
        Should return 302 to detail page on successful POST and have tag
        and suggestion saved to event
        """
        self.assertEqual(len(self.event.suggestions.all()), 0)
        self.client.login(username=self.credential, password=self.credential)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

        tag = 'foo'
        params = {
            'title': self.event.title,
            'tags': tag,
            'suggestions-TOTAL_FORMS': '1',
            'suggestions-INITIAL_FORMS': '0',
            'suggestions-MAX_NUM_FORMS': '1000',
            'suggestions-0-from_date': '2014-01-01',
            'suggestions-0-to_date': '2014-01-02',
        }
        response = self.client.post(self.url, params)
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse('cosinnus:event:entry-detail', kwargs=self.kwargs),
            response.get('location'))

        # re-get edited event from database
        self.event = Event.objects.get(pk=self.event.pk)
        num_tags = len(self.event.tags.filter(name=tag))
        self.assertEqual(num_tags, 1)
        self.assertEqual(len(self.event.suggestions.all()), 1)

    def test_other_user(self):
        """
        Should redirect to list page instead of edit
        """
        credential = 'test'
        self.add_user(credential)
        self.client.login(username=credential, password=credential)
        response = self.client.get(self.url, follow=True)
        self.assertEqual(response.status_code, 200)

        kwargs = {'group': self.group.slug}
        list_url = reverse('cosinnus:event:list', kwargs=kwargs)
        self.assertRedirects(response, list_url)
