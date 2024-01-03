# -*- coding: utf-8 -*-
import uuid
import time
import requests

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.shortcuts import reverse
from django.conf import settings
from django.core.exceptions import PermissionDenied, ImproperlyConfigured

from cosinnus.models.bbb_room import BBBRoom
from cosinnus.models import CosinnusGroup, CosinnusGroupMembership
from cosinnus.utils import bigbluebutton as bbb_utils

from cosinnus.views.bbb_room import BBBRoomMeetingView
from cosinnus.apis.bigbluebutton import BigBlueButtonAPI


if settings.COSINNUS_CONFERENCES_ENABLED:

    class BBBRoomTest(TestCase):

        bbb_api = None # initialized in setUp

        def setUp(self):

            try:
                self.bbb_api = BigBlueButtonAPI()
            except ImproperlyConfigured:
                self.skipTest("BBB module is not configured properly. Please enter a valid secret key.")
                return

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
                source_object=self.group,
            )

            self.assertEqual(room.name, "TestName")
            self.assertIN("MeetingID-", room.meeting_id)
            self.assertEqual(room.welcome_message, "Welcome Test")

            time.sleep(2)

            room_info = self.bbb_api.meeting_info(room.meeting_id, room.moderator_password)
            self.assertNotEqual(room_info, None)
            self.assertEqual(room_info['moderatorPW'], room.moderator_password)
            self.assertEqual(room_info['attendeePW'], room.attendee_password)

            room_info = self.bbb_api.meeting_info(room.meeting_id, room.moderator_password)

        def test_option_creation(self):
            room_options = {
                "autoStartRecording": False,
                "allowStartStopRecording": False,
                "muteOnStart": True
            }

            room = BBBRoom.create(
                name="OptionTest",
                meeting_id="OptionMeetingID",
                options=room_options
            )

            expected_options = settings.BBB_DEFAULT_CREATE_PARAMETERS
            expected_options.update(room_options)

            self.assertEqual(room.name, "OptionTest")
            self.assertEqual(room.meeting_id, "OptionMeetingID")
            self.assertEqual(room.welcome_message, "Option Test")
            self.assertEqual(room.options, expected_options)

            time.sleep(2)

            room_info = self.bbb_api.meeting_info(room.meeting_id, room.moderator_password)
            self.assertNotEqual(room_info, None)
            self.assertEqual(room_info['moderatorPW'], room.moderator_password)
            self.assertEqual(room_info['attendeePW'], room.attendee_password)

        def test_user_joining(self):
            room = BBBRoom.create(
                name="JOIN TEST",
                meeting_id="join-test",
            )

            time.sleep(2)

            room.join_group_members(self.group)

            # test joining as attendee
            xml_result = self.bbb_api.xml_join("Example Name", room.meeting_id, room.attendee_password)
            self.assertNotEqual(xml_result, None)
            json_result = bbb_utils.xml_to_json(xml_result)
            self.assertEqual(json_result['returncode'], "SUCCESS")
            self.assertEqual(json_result['meeting_id'], room.internal_meeting_id)
            self.assertEqual(json_result['messageKey'], 'successfullyJoined')

            # test joining as moderator
            xml_result = self.bbb_api.xml_join("Moderator Name", room.meeting_id, room.moderator_password)
            self.assertNotEqual(xml_result, None)
            json_result = bbb_utils.xml_to_json(xml_result)
            self.assertEqual(json_result['returncode'], "SUCCESS")
            self.assertEqual(json_result['meeting_id'], room.internal_meeting_id)
            self.assertEqual(json_result['messageKey'], 'successfullyJoined')

            # test joining with wrong credentials
            xml_result = self.bbb_api.xml_join("No Name", room.meeting_id, "abcdefg")
            self.assertEqual(xml_result, None)

            # test meeting info participant count information
            info = self.bbb_api.meeting_info(room.meeting_id, room.moderator_password)

            # self.assertEqual(info.get('participantCount', -1), 2)

        def test_room_restart(self):
            room = BBBRoom.create(
                name="RESTART TEST",
                meeting_id="restart-test",
            )

            time.sleep(2)
            room.join_group_members(self.group)

            room_info = self.bbb_api.meeting_info(room.meeting_id, room.moderator_password)
            self.assertNotEqual(room_info, None)
            self.assertEqual(room_info['moderatorPW'], room.moderator_password)
            self.assertEqual(room_info['attendeePW'], room.attendee_password)

            room.end()
            time.sleep(2)
            """ TODO: this restart() fails on BBBatscale but works on a direct BBB server!
                Also, after a room has been end()ed like this, it cannot be recreated by a new call
                to create(), and will forever stay broken! """
            room.restart()

            room_info = self.bbb_api.meeting_info(room.meeting_id, room.moderator_password)
            self.assertNotEqual(room_info, None)
            self.assertEqual(room_info['moderatorPW'], room.moderator_password)
            self.assertEqual(room_info['attendeePW'], room.attendee_password)

            room.end()

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
            )

            time.sleep(2)

            room.join_group_members(self.group)

            # end room with bbb library
            xml_result = self.bbb_api.end_meeting(room.meeting_id, room.moderator_password)
            self.assertNotEqual(xml_result, 'error')
            self.assertEqual(xml_result, True)

        # THERE IS CURRENTLY NO FUNCTION TO JOIN A USER TO A ROOM AND EMULATE A RUNNING MEETING
        # def test_remote_running(self):
        #     room = BBBRoom.create(
        #         name="REMOTE TEST",
        #         meeting_id="remote-test",
        #     )
        #
        #     time.sleep(2)
        #
        #     room2 = BBBRoom.create(
        #         name="RUNNING TEST",
        #         meeting_id="running-test",
        #     )
        #     time.sleep(2)
        #
        #     room.join_group_members(self.group)
        #     room2.join_group_members(self.group)
        #
        #     room.end()
        #
        #     join_url = bbb.xml_join("USER NAME", room2.meeting_id, room2.attendee_password)
        #     print(join_url)

        def test_join_view(self):
            factory = RequestFactory()

            room = BBBRoom.create(
                name="VIEW TEST",
                meeting_id="view-test",
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

            self.assertTrue(first_token.startswith(self.bbb_api.api_auth_url))

            # another request with another user
            request = factory.get(reverse("cosinnus:bbb-room", kwargs={"room_id": room.id}))
            request.user = self.attendee

            response = BBBRoomMeetingView.as_view()(request, **{"room_id": room.id})

            self.assertNotEqual(response.status_code, 404)
            self.assertNotEqual(response.status_code, 403)
            self.assertEqual(response.status_code, 302)

            second_token = response.url

            self.assertNotEqual(first_token, second_token)
            self.assertTrue(second_token.startswith(self.bbb_api.api_auth_url))

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
            self.assertTrue(second_token.startswith(self.bbb_api.api_auth_url))

        def tearDown(self):
            for room in BBBRoom.objects.all():
                room.end()
