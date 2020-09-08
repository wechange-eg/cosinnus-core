import argparse
import urllib
import requests

from hashlib import sha1, sha256

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.translation import ugettext as _
from django_bigbluebutton.bbb import BigBlueButton
from django_bigbluebutton.utils import xml_to_json, parse_xml

""" 
This is a wrapper for django-bigbluebutton.bbb

Some features are not present in bbb.py; for instance a meeting creation with a `max_attendees` value.
Therefore we create a create_verbose_meeting function, to address these properties of a BBBRoom 
we need in the WeChange project.

Functions that are not included in bbb.py are called `manually` via urllib.
For a full documentation on BigBlueButton API parameters have a look at: https://docs.bigbluebutton.org/dev/api.html

Checksum for API parameters is generated with SHA1 instead of SHA256 hash by default. Set the used hash algorithm in the 
global settings in `BBB_HASH_ALGORITHM`.
All wrapped functions from bbb.py are called with sha1, regardless of the `BBB_HASH_ALGORITHM` setting.
"""


def api_call(self, query, call):
    prepared = '{}{}{}'.format(call, query, self.secret_key)

    if settings.BBB_HASH_ALGORITHM == "SHA1":
        checksum = sha1(str(prepared).encode('utf-8')).hexdigest()
    elif settings.BBB_HASH_ALGORITHM == "SHA256":
        checksum = sha256(str(prepared).encode('utf-8')).hexdigest()
    else:
        raise ImproperlyConfigured("BBB_HASH_ALGORITHM setting is not set to SHA1 or SHA256")

    result = "%s&checksum=%s" % (query, checksum)
    return result


def start(name, meeting_id, welcome="Welcome to the conversation", moderator_password="",
          attendee_password=""):
    """ This function is a wrapper for bbb.start() with all its parameters

    :param name: Human readable name for the meeting
    :type: str

    :param meeting_id: Human readable ID for the meeting
    :type: str

    :param welcome: Welcome message when joining the meeting
    :type: str

    :param moderator_password: Password for users to join with moderator privileges
    :type: str

    :param attendee_password: Password for users to join with default attendee privileges
    :type: str

    :return: XML representation of the API result
    :rtype: XML
    """

    m_xml = BigBlueButton().start(
        name=name, meeting_id=meeting_id, welcome=welcome, attendee_password=attendee_password,
        moderator_password=moderator_password
    )

    meeting_json = xml_to_json(m_xml)
    if meeting_json['returncode'] != 'SUCCESS':
        # TODO add logging statement
        raise ValueError('Unable to create meeting!')

    return m_xml


def start_verbose(
        meeting_name, meeting_id, welcome_message="Welcome to the conversation",
        moderator_password="", attendee_password="", max_participants=None, dial_number=None, voice_bridge=None,
        parent_meeting_id=None):
    """ This function calls the BigBlueButton API directly to create a meeting with all available parameters available
        in the cosinnus-core.BBBRoom model.

    :param meeting_name: Human readable name for the meeting
    :type: str

    :param meeting_id: Human readable ID for the meeting
    :type: str

    :param welcome_message: Welcome message when joining the meeting
    :type: str

    :param moderator_password: Password for users to join with moderator privileges
    :type: str

    :param attendee_password: Password for users to join with default attendee privileges
    :type: str

    :param max_participants: Number of users allowed in the conference
    :type: int

    :param voice_bridge: Dial in PIN for telephone users
    :type: int

    :param parent_meeting_id: Breaking room for a running conference
    :type: str

    :return: XML representation of the API result
    :rtype: XML
    """
    call = 'create'

    query = urllib.parse.urlencode(
        ("name", meeting_name),
        ('meetingID', meeting_id),
        ("welcome", welcome_message),
    )

    if max_participants and type(max_participants, int):
        query += (("maxParticipants", max_participants),)

    if dial_number and type(dial_number, int):
        query += (("dialNumber", dial_number),)

    if voice_bridge and type(dial_number, int):
        query += (("voiceBridge", voice_bridge),)

    if parent_meeting_id:
        query += ("parentMeetingID", parent_meeting_id)

    hashed = api_call(query, call)
    url = settings.BBB_API_URL + call + '?' + hashed
    result = parse_xml(requests.get(url).content.decode('utf-8'))

    if result:
        return result
    else:
        raise


def end_meeting(meeting_id, password):
    """ This function is a wrapper for the `end_meeting` function in bbb.py """

    m_xml = BigBlueButton().end_meeting(
        meeting_id=meeting_id, password=password
    )

    meeting_json = xml_to_json(m_xml)
    if meeting_json['returncode'] != 'SUCCESS':
        # TODO add logging statement
        raise ValueError('Unable to create meeting!')

    return m_xml


def get_meetings():
    """ This function is a wrapper for the `get_meetings` function in bbb.py

    :return: XML representation of the API result
    :rtype: XML
    """
    return BigBlueButton().get_meetings()


def meeting_info(meeting_id, password):
    """ This function is a wrapper for the `meeting_info` function in bbb.py

    :return: XML representation of the API result
    :rtype: XML
    """
    return BigBlueButton().meeting_info(meeting_id, password)


def is_running(self, meeting_id):
    """ This function is a wrapper for the `is_running` function in bbb.py

    :return: XML representation of the API result
    :rtype: XML
    """
    return BigBlueButton().is_running(meeting_id)


def join_url(self, meeting_id, name, password):
    """ This function is a wrapper for the `join_url` function in bbb.py

    :return: XML representation of the API result
    :rtype: XML
    """
    return BigBlueButton().is_running(meeting_id)
