import datetime
from typing import List, Optional, Tuple, Type
from unittest.mock import patch

from django.contrib.admin import AdminSite, ModelAdmin
from django.contrib.auth import get_user_model
from django.contrib.messages.api import get_messages
from django.contrib.messages.storage.base import Message
from django.contrib.messages.storage.fallback import FallbackStorage
from django.db.models import Model, QuerySet
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

import cosinnus.models.membership
from cosinnus.admin import UserAdmin
from cosinnus.models import BaseTagObject, CosinnusIdea
from cosinnus.models.group_extra import CosinnusSociety
from cosinnus_etherpad.models import Ethercalc, Etherpad
from cosinnus_event.models import Comment as EventComment
from cosinnus_event.models import Event
from cosinnus_file.models import FileEntry
from cosinnus_marketplace.models import Comment as OfferComment
from cosinnus_marketplace.models import Offer
from cosinnus_note.models import Comment as NoteComment
from cosinnus_note.models import Note
from cosinnus_poll.models import Comment as PollComment
from cosinnus_poll.models import Poll
from cosinnus_todo.models import Comment as TodoComment
from cosinnus_todo.models import TodoEntry

User = get_user_model()
VISIBILITY_USER = BaseTagObject.VISIBILITY_USER
VISIBILITY_GROUP = BaseTagObject.VISIBILITY_GROUP


def call_admin_action(
    admin_class: Type[ModelAdmin], model: Type[Model], action_name: str, queryset: QuerySet, user: User
) -> Tuple[Optional[HttpResponse], List[Message]]:
    request = RequestFactory().post('/')
    request.user = user

    setattr(request, 'session', 'session')
    messages = FallbackStorage(request)
    setattr(request, '_messages', messages)

    model_admin = admin_class(model, AdminSite())
    action_func = getattr(model_admin, action_name)

    result = action_func(request, queryset)

    messages = [message for message in get_messages(request)]

    return result, messages


class TestDeactivateSpamUsers(TestCase):
    def setUp(self):
        # we create etherpad/ethercalc objects but do not want to initialize the actual etherpads / ethercalcs
        etherpad_patch = patch('cosinnus_etherpad.models.Etherpad.init_client', return_value=None)
        etherpad_patch.start()
        self.addCleanup(etherpad_patch.stop)
        ethercalc_patch = patch('cosinnus_etherpad.models.Ethercalc.init_client', return_value=None)
        ethercalc_patch.start()
        self.addCleanup(ethercalc_patch.stop)

        self.admin_user = User.objects.create_superuser(username='admin')
        self.spam_user = User.objects.create(username='spamuser')
        self.regular_user = User.objects.create(username='regularuser')

        self.spam_group = CosinnusSociety.objects.create(name='TestGroup')
        self.regular_group = CosinnusSociety.objects.create(name='TestGroup')
        self.spam_group.memberships.create(user=self.spam_user, status=cosinnus.models.membership.MEMBERSHIP_ADMIN)
        self.regular_group.memberships.create(
            user=self.regular_user, status=cosinnus.models.membership.MEMBERSHIP_ADMIN
        )
        self.regular_group.memberships.create(user=self.spam_user, status=cosinnus.models.membership.MEMBERSHIP_ADMIN)

        self.spam_idea = CosinnusIdea.objects.create(title='spam idea', creator=self.spam_user)
        self.spam_note = Note.objects.create(
            group=self.regular_group, creator=self.spam_user, title='title', text='text'
        )
        self.spam_event = Event.objects.create(
            group=self.regular_group,
            creator=self.spam_user,
            title='title',
            note='text',
            from_date=datetime.datetime.fromisoformat('2026-01-01T10:00:00+00:00'),
            to_date=datetime.datetime.fromisoformat('2026-01-01T15:00:00+00:00'),
        )
        self.spam_poll = Poll.objects.create(
            group=self.regular_group,
            creator=self.spam_user,
            title='title',
        )
        self.spam_todo = TodoEntry.objects.create(
            group=self.regular_group,
            creator=self.spam_user,
            title='title',
        )
        self.spam_offer = Offer.objects.create(
            group=self.regular_group,
            creator=self.spam_user,
            title='title',
        )
        self.spam_file = FileEntry.objects.create(
            group=self.regular_group,
            creator=self.spam_user,
            title='title',
        )
        self.spam_etherpad = Etherpad.objects.create(
            group=self.regular_group,
            creator=self.spam_user,
            title='title',
        )
        self.spam_ethercalc = Ethercalc.objects.create(
            group=self.regular_group,
            creator=self.spam_user,
            title='title',
        )

        self.regular_idea = CosinnusIdea.objects.create(title='regular idea', creator=self.regular_user)
        self.regular_note = Note.objects.create(
            group=self.regular_group, creator=self.regular_user, title='title', text='text'
        )
        self.regular_event = Event.objects.create(
            group=self.regular_group,
            creator=self.regular_user,
            title='title',
            note='text',
            from_date=datetime.datetime.fromisoformat('2026-01-01T10:00:00+00:00'),
            to_date=datetime.datetime.fromisoformat('2026-01-01T15:00:00+00:00'),
        )
        self.regular_poll = Poll.objects.create(
            group=self.regular_group,
            creator=self.regular_user,
            title='title',
        )
        self.regular_todo = TodoEntry.objects.create(
            group=self.regular_group,
            creator=self.regular_user,
            title='title',
        )
        self.regular_offer = Offer.objects.create(
            group=self.regular_group,
            creator=self.regular_user,
            title='title',
        )
        self.regular_file = FileEntry.objects.create(
            group=self.regular_group,
            creator=self.regular_user,
            title='title',
        )
        self.regular_etherpad = Etherpad.objects.create(
            group=self.regular_group,
            creator=self.regular_user,
            title='title',
        )
        self.regular_ethercalc = Ethercalc.objects.create(
            group=self.regular_group,
            creator=self.regular_user,
            title='title',
        )

        # comments from spam user and regular user
        for _creator in [self.spam_user, self.regular_user]:
            NoteComment.objects.create(note=self.regular_note, creator=_creator, text='comment text')
            EventComment.objects.create(event=self.regular_event, creator=_creator, text='comment text')
            PollComment.objects.create(poll=self.regular_poll, creator=_creator, text='comment text')
            TodoComment.objects.create(todo=self.regular_todo, creator=_creator, text='comment text')
            OfferComment.objects.create(offer=self.regular_offer, creator=_creator, text='comment text')

    def _assert_hidden(self, obj):
        """
        reloads the object with media_tag from the database and asserts visibility only to creator
        """
        fresh_obj = type(obj).objects.select_related('media_tag').get(pk=obj.pk)
        self.assertEqual(fresh_obj.media_tag.visibility, VISIBILITY_USER)

    def _assert_visible(self, obj):
        """
        reloads the object with media_tag from the database and asserts visibility to group
        """
        fresh_obj = type(obj).objects.select_related('media_tag').get(pk=obj.pk)
        self.assertEqual(fresh_obj.media_tag.visibility, VISIBILITY_GROUP)

    def test_deactivate_spam_user(self):
        queryset = User.objects.filter(pk=self.spam_user.id)
        result, messages = call_admin_action(UserAdmin, User, 'deactivate_spam_users', queryset, self.admin_user)

        # verify action return values
        with self.subTest('action result'):
            self.assertIsNone(result)

        with self.subTest('action messages'):
            self.assertEqual(1, len(messages))
            message = messages[0]
            self.assertEqual(message.level_tag, 'info')

            expected_message = """1 User account(s) were deactivated successfully. 
1 groups and projects have been deactivated. 
8 contents have been set invisible. 
6 contents have been deleted immediately. 
The user(s) will be deleted after 30 days."""
            self.assertEqual(message.message, expected_message)

        # verify action on spam content
        with self.subTest('spam user deactivated'):
            self.spam_user.refresh_from_db()
            self.assertFalse(self.spam_user.is_active)

        with self.subTest('spam user group deactivated'):
            self.spam_group.refresh_from_db()
            self.assertFalse(self.spam_group.is_active)

        with self.subTest('spam user note hidden'):
            self._assert_hidden(self.spam_note)

        with self.subTest('spam user event hidden'):
            self._assert_hidden(self.spam_event)

        with self.subTest('spam user poll hidden'):
            self._assert_hidden(self.spam_poll)

        with self.subTest('spam user todo hidden'):
            self._assert_hidden(self.spam_todo)

        with self.subTest('spam user offer hidden'):
            self._assert_hidden(self.spam_offer)

        with self.subTest('spam user file hidden'):
            self._assert_hidden(self.spam_file)

        with self.subTest('spam user etherpad hidden'):
            self._assert_hidden(self.spam_etherpad)

        with self.subTest('spam user ethercalc hidden'):
            self._assert_hidden(self.spam_ethercalc)

        with self.subTest('spam user idea deleted'):
            self.assertFalse(CosinnusIdea.objects.filter(creator=self.spam_user).exists())

        with self.subTest('spam user note comment deleted'):
            self.assertFalse(NoteComment.objects.filter(creator=self.spam_user).exists())

        with self.subTest('spam user event comment deleted'):
            self.assertFalse(EventComment.objects.filter(creator=self.spam_user).exists())

        with self.subTest('spam user poll comment deleted'):
            self.assertFalse(PollComment.objects.filter(creator=self.spam_user).exists())

        with self.subTest('spam user todo comment deleted'):
            self.assertFalse(TodoComment.objects.filter(creator=self.spam_user).exists())

        with self.subTest('spam user offer comment deleted'):
            self.assertFalse(OfferComment.objects.filter(creator=self.spam_user).exists())

        # verify action no-op on regular content
        with self.subTest('regular user not deactivated'):
            self.regular_user.refresh_from_db()
            self.assertTrue(self.regular_user.is_active)

        with self.subTest('regular user group not deactivated'):
            self.regular_group.refresh_from_db()
            self.assertTrue(self.regular_group.is_active)

        with self.subTest('regular user note visible'):
            self._assert_visible(self.regular_note)

        with self.subTest('regular user event visible'):
            self._assert_visible(self.regular_event)

        with self.subTest('regular user poll visible'):
            self._assert_visible(self.regular_poll)

        with self.subTest('regular user todo visible'):
            self._assert_visible(self.regular_todo)

        with self.subTest('regular user offer visible'):
            self._assert_visible(self.regular_offer)

        with self.subTest('regular user file visible'):
            self._assert_visible(self.regular_file)

        with self.subTest('regular user etherpad visible'):
            self._assert_visible(self.regular_etherpad)

        with self.subTest('regular user ethercalc visible'):
            self._assert_visible(self.regular_ethercalc)

        with self.subTest('regular user idea not deleted'):
            self.assertTrue(CosinnusIdea.objects.filter(creator=self.regular_user).exists())

        with self.subTest('regular user note comment not deleted'):
            self.assertTrue(NoteComment.objects.filter(creator=self.regular_user).exists())

        with self.subTest('regular user event comment not deleted'):
            self.assertTrue(EventComment.objects.filter(creator=self.regular_user).exists())

        with self.subTest('regular user poll comment not deleted'):
            self.assertTrue(PollComment.objects.filter(creator=self.regular_user).exists())

        with self.subTest('regular user todo comment not deleted'):
            self.assertTrue(TodoComment.objects.filter(creator=self.regular_user).exists())

        with self.subTest('regular user offer comment not deleted'):
            self.assertTrue(OfferComment.objects.filter(creator=self.regular_user).exists())
