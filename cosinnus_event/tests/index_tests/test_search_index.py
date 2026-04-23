from django.test import TestCase

from cosinnus.models import CosinnusGroup
from cosinnus_event.models import Event
from cosinnus_event.search_indexes import EventIndex


class EventIndexFilterTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.group = CosinnusGroup.objects.create(name='Test Group')

        cls.indexed_events = []
        cls.indexed_events.append(
            Event.objects.create(
                title='Scheduled Event',
                group=cls.group,
                state=Event.STATE_SCHEDULED,
            )
        )

        cls.not_indexed_events = []
        cls.not_indexed_events.append(
            Event.objects.create(
                title='Scheduled Hidden Proxy Event',
                group=cls.group,
                state=Event.STATE_SCHEDULED,
                is_hidden_group_proxy=True,
            )
        )
        cls.not_indexed_events.append(
            Event.objects.create(
                title='Open Event',
                group=cls.group,
                state=Event.STATE_VOTING_OPEN,
            )
        )
        cls.not_indexed_events.append(
            Event.objects.create(
                title='Canceled Event',
                group=cls.group,
                state=Event.STATE_CANCELED,
            )
        )
        cls.not_indexed_events.append(
            Event.objects.create(
                title='Archived Doodle Event',
                group=cls.group,
                state=Event.STATE_ARCHIVED_DOODLE,
            )
        )
        cls.not_indexed_events.append(
            Event.objects.create(title='Hidden Proxy', group=cls.group, is_hidden_group_proxy=True)
        )

    def setUp(self):
        self.event_index = EventIndex()  # does not work in setUpTestData

    def _test_event_is_indexed(self, event: Event, should_be_indexed: bool):
        """Tests, if an event is indexed and updated as intended"""
        qs = self.event_index.index_queryset()

        if should_be_indexed:
            self.assertIn(event, qs)
            self.assertTrue(self.event_index.should_update(event))
        else:
            self.assertNotIn(event, qs)
            self.assertFalse(self.event_index.should_update(event))

    def test_indexed_event_types(self):
        for event in self.indexed_events:
            with self.subTest(event_type=event.title):
                self._test_event_is_indexed(event, should_be_indexed=True)

    def test_not_indexed_event_types(self):
        for event in self.not_indexed_events:
            with self.subTest(event_type=event.title):
                self._test_event_is_indexed(event, should_be_indexed=False)
