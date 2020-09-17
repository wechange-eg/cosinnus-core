# -*- coding: utf-8 -*-
import uuid
import time
import requests

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.shortcuts import reverse
from django.conf import settings
from django.core.exceptions import PermissionDenied

from cosinnus.models.bbb_room import BBBRoom
from cosinnus.apis import bigbluebutton as bbb
from cosinnus.models import CosinnusGroup, CosinnusGroupMembership

from cosinnus.views.bbb_room import BBBRoomMeetingView


class BBBRoomTest(TestCase):
    def setUp(self):
        self.moderator = User.objects.create_user(
            username="moderator",
            email="moderator@example.org",
            is_superuser=True,
            is_staff=True
        )

        self.attendee = User.objects.create_user(
            username="attendee",
            email="attendee@example.org",
            is_superuser=True,
            is_staff=True
        )

        self.outsider = User.objects.create_user(
            username="outsider",
            email="outsider@example.org",
        )

        self.group = CosinnusGroup(name="BBB Test")
        self.group.save()

        membership = CosinnusGroupMembership(group=self.group, user=self.moderator, status=2)
        membership.save()

        membership = CosinnusGroupMembership(group=self.group, user=self.attendee, status=1)
        membership.save()

    def test_creation(self):
        room = BBBRoom.create(
            name="TestName",
            meeting_id="MeetingID",
            meeting_welcome="Welcome Test",
        )

        self.assertEqual(room.name, "TestName")
        self.assertEqual(room.meeting_id, "MeetingID")
        self.assertEqual(room.welcome_message, "Welcome Test")

        time.sleep(2)

        room_info = bbb.meeting_info(room.meeting_id, room.moderator_password)
        self.assertNotEqual(room_info, None)
        self.assertEqual(room_info['moderator_pw'], room.moderator_password)
        self.assertEqual(room_info['attendee_pw'], room.attendee_password)

    def test_user_joining(self):
        room = BBBRoom.create(
            name="JOIN TEST",
            meeting_id="join-test",
            meeting_welcome="join the meeting",
        )

        time.sleep(2)

        room.join_group_members(self.group)

        # test joining as attendee
        xml_result = bbb.xml_join("Example Name", room.meeting_id, room.attendee_password)
        self.assertNotEqual(xml_result, None)
        json_result = bbb.xml_to_json(xml_result)
        self.assertEqual(json_result['returncode'], "SUCCESS")
        self.assertEqual(json_result['meeting_id'], room.internal_meeting_id)
        self.assertEqual(json_result['messageKey'], 'successfullyJoined')

        # test joining as moderator
        xml_result = bbb.xml_join("Moderator Name", room.meeting_id, room.moderator_password)
        self.assertNotEqual(xml_result, None)
        json_result = bbb.xml_to_json(xml_result)
        self.assertEqual(json_result['returncode'], "SUCCESS")
        self.assertEqual(json_result['meeting_id'], room.internal_meeting_id)
        self.assertEqual(json_result['messageKey'], 'successfullyJoined')

        # test joining with wrong credentials
        xml_result = bbb.xml_join("No Name", room.meeting_id, "abcdefg")
        self.assertEqual(xml_result, None)

    def test_membership_signals(self):
        moderator = User.objects.create_user(
            username="signal_moderator",
            email="signalmoderator@example.org",
            is_superuser=True,
            is_staff=True
        )

        attendee = User.objects.create_user(
            username="signal_attendee",
            email="signalattendee@example.org",
            is_superuser=True,
            is_staff=True
        )

        outsider = User.objects.create_user(
            username="signal_outsider",
            email="signaloutsider@example.org",
            is_superuser=True,
            is_staff=True
        )

        group = CosinnusGroup(name="BBB Test")
        group.save()

        membership1 = CosinnusGroupMembership(group=group, user=moderator, status=2)
        membership1.save()

        membership2 = CosinnusGroupMembership(group=group, user=attendee, status=1)
        membership2.save()

        room = BBBRoom.create(
            name="SIGNAL TEST",
            meeting_id="signal-test",
            meeting_welcome="meant to be end",
        )

        time.sleep(2)
        room.join_group_members(group)

        membership1.status = 1

        membership1.save()
        self.assertEqual(len(room.moderators.all()), 1)

        membership2.delete()
        self.assertEqual(len(room.attendees.all()), 1)

        # membership3 = CosinnusGroupMembership(group=group, user=outsider, status=1)
        # membership3.save()
        # self.assertEqual(len(room.attendees.all()), 2)

    def test_end_meeting_via_bbb(self):
        room = BBBRoom.create(
            name="END TEST",
            meeting_id="end-test",
            meeting_welcome="meant to be end",
        )

        time.sleep(2)

        room.join_group_members(self.group)

        # end room with bbb library
        xml_result = bbb.end_meeting(room.meeting_id, room.moderator_password)
        self.assertNotEqual(xml_result, 'error')
        self.assertEqual(xml_result, True)

    def test_join_view(self):

        factory = RequestFactory()

        room = BBBRoom.create(
            name="VIEW TEST",
            meeting_id="end-test",
            meeting_welcome="join via url",
        )

        time.sleep(2)
        room.join_group_members(self.group)

        request = factory.get(reverse("cosinnus:bbb-room", kwargs={"room_id": room.id}))
        request.user = self.moderator

        response = BBBRoomMeetingView.as_view()(request, **{"room_id": room.id})

        self.assertNotEqual(response.status_code, 404)
        self.assertNotEqual(response.status_code, 403)
        self.assertEqual(response.status_code, 302)

        first_token = response.url

        self.assertTrue(first_token.startswith(settings.BBB_SERVER))

        # another request with another user
        request = factory.get(reverse("cosinnus:bbb-room", kwargs={"room_id": room.id}))
        request.user = self.attendee

        response = BBBRoomMeetingView.as_view()(request, **{"room_id": room.id})

        self.assertNotEqual(response.status_code, 404)
        self.assertNotEqual(response.status_code, 403)
        self.assertEqual(response.status_code, 302)

        second_token = response.url

        self.assertNotEqual(first_token, second_token)
        self.assertTrue(second_token.startswith(settings.BBB_SERVER))

        # third request as anonymous user should result in a 403
        request = factory.get(reverse("cosinnus:bbb-room", kwargs={"room_id": room.id}))
        request.user = self.outsider

        with self.assertRaises(PermissionDenied):
            BBBRoomMeetingView.as_view()(request, **{"room_id": room.id})

        # test view with superuser permissions
        superuser = User.objects.create_user(
            username="superuser",
            email="superuser@example.org",
            is_superuser=True,
            is_staff=True
        )
        request = factory.get(reverse("cosinnus:bbb-room", kwargs={"room_id": room.id}))
        request.user = superuser

        response = BBBRoomMeetingView.as_view()(request, **{"room_id": room.id})

        self.assertNotEqual(response.status_code, 404)
        self.assertNotEqual(response.status_code, 403)
        self.assertEqual(response.status_code, 302)

        second_token = response.url

        self.assertNotEqual(first_token, second_token)
        self.assertTrue(second_token.startswith(settings.BBB_SERVER))

    def tearDown(self):
        for room in BBBRoom.objects.all():
            room.end()
