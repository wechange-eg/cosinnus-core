# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.timezone import now

from cosinnus_event.models import Event, Suggestion, Vote
from cosinnus_event.tests.view_tests.base import ViewTestCase
from cosinnus.models.tagged import BaseTagObject


class VoteTest(ViewTestCase):

    def test_vote(self):
        """
        Should be able to vote on an event's suggestion
        """
        event = Event.objects.create(
            group=self.group,
            creator=self.admin,
            public=True,
            title='testevent',
            from_date=now(),
            to_date=now(),
            state=Event.STATE_VOTING_OPEN)
        event.media_tag.visibility = BaseTagObject.VISIBILITY_ALL
        event.media_tag.save()
        suggestion = Suggestion.objects.create(
            from_date=event.from_date,
            to_date=event.to_date,
            event=event)
        kwargs = {'group': self.group.slug, 'slug': event.slug}
        url = reverse('cosinnus:event:doodle-vote', kwargs=kwargs)

        self.client.login(username=self.credential, password=self.credential)
        response = self.client.get(url)

        # should return 200 and have event in context
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['object'], event)

        # now cast the vote
        params = {
            'csrfmiddlewaretoken': response.cookies['csrftoken'].value,
            'form-TOTAL_FORMS': '1',
            'form-INITIAL_FORMS': '0',
            'form-MAX_NUM_FORMS': '1000',
            'form-0-suggestion': force_str(suggestion.pk),
            'form-0-choice': '1',
        }
        response = self.client.post(url, params)
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            reverse('cosinnus:event:doodle-vote', kwargs=kwargs),
            response.get('location'))

        vote = Vote.objects.all()[0]
        self.assertEqual(vote.voter, self.admin)
        self.assertEqual(vote.suggestion, suggestion)
