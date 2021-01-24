from hashlib import sha1, sha256
import logging
import urllib

from django.core.exceptions import ImproperlyConfigured
import requests

from cosinnus.conf import settings
from cosinnus.models import CosinnusPortal, get_domain_for_portal
from cosinnus.utils import bigbluebutton as bbb_utils
from cosinnus.utils.functions import is_number


logger = logging.getLogger('cosinnus')


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

def get_current_bbb_server_auth_pair():
    """ Central helper function to retrieve the currently
        selected BBB-server API URL and Secret.
        
        @return: tuple of (str: BBB_API_URL, str: BBB_SECRET_KEY) if a server is set, 
                    or (None, None) if no server is set """
    portal = CosinnusPortal.get_current()
    try:
        auth_pair = dict(settings.COSINNUS_BBB_SERVER_AUTH_PAIRS).get(portal.bbb_server)
        ret = (auth_pair[0], auth_pair[1]) # force fail on improper tuple
        return ret
    except Exception as e:
        logger.error('Misconfigured: Either COSINNUS_BBB_SERVER_CHOICES or COSINNUS_BBB_SERVER_AUTH_PAIRS are not properly set up!',
            extra={'exception': e})
    return (None, None)


def get_current_bbb_server_auth_pair_or_raise():
    api_url, secret = get_current_bbb_server_auth_pair()
    if not api_url or not secret:
        raise ImproperlyConfigured("No valid BBB server auth is currently configured or selected as active for this portal!")
    return (api_url, secret)


def join_url_tokenized(meeting_id, name, password):
    url = join_url(meeting_id, name, password)
    return requests.get(url).url


def api_call(query, call):
    __, secret = get_current_bbb_server_auth_pair_or_raise()
    prepared = '{}{}{}'.format(call, query, secret)

    if settings.BBB_HASH_ALGORITHM == "SHA1":
        checksum = sha1(str(prepared).encode('utf-8')).hexdigest()
    elif settings.BBB_HASH_ALGORITHM == "SHA256":
        checksum = sha256(str(prepared).encode('utf-8')).hexdigest()
    else:
        raise ImproperlyConfigured("BBB_HASH_ALGORITHM setting is not set to SHA1 or SHA256")

    result = "%s&checksum=%s" % (query, checksum)
    return result


def start(
        name, meeting_id, welcome="Welcome to the conversation",
        moderator_password="", attendee_password="", max_participants=None, voice_bridge=None,
        parent_meeting_id=None, options=None, presentation_url=""):
    """ This function calls the BigBlueButton API directly to create a meeting with all available parameters available
        in the cosinnus-core.BBBRoom model.

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

    :param max_participants: Number of users allowed in the conference
    :type: int

    :param voice_bridge: Dial in PIN for telephone users
    :type: int

    :param parent_meeting_id: Breaking room for a running conference
    :type: str

    :param options: BBBRoom options according to the listed options in the BigBlueButton API
    :type: dict

    :param presentation_url: Publicly available URL of presentation file to be pre-uploaded as slides to BBB room
    :type: str

    :return: XML representation of the API result
    :rtype: XML
    """
    
    api_url = get_current_bbb_server_auth_pair_or_raise()[0]
    call = 'create'

    # set default values
    voice_bridge = voice_bridge if voice_bridge and is_number(voice_bridge) else bbb_utils.random_voice_bridge()
    attendee_password = attendee_password if attendee_password else bbb_utils.random_password()
    moderator_password = moderator_password if moderator_password else bbb_utils.random_password()

    query = (
        ("name", name),
        ('meetingID', meeting_id),
        ("welcome", welcome),
        ("voiceBridge", voice_bridge),
        ("attendeePW", attendee_password),
        ("moderatorPW", moderator_password),
    )

    if max_participants and is_number(max_participants):
        query += (("maxParticipants", int(max_participants)),)

    if parent_meeting_id:
        query += (("parentMeetingID", parent_meeting_id),)

    if options:
        for key, value in options.items():
            query += ((key, value),)

    query = urllib.parse.urlencode(query)

    hashed = api_call(query, call)
    url = api_url + call + '?' + hashed
    # Presentation file has to be sent via POST request with XML body
    if presentation_url:
        headers = {'Content-Type': 'application/xml'}
        xml = "<?xml version='1.0' encoding='UTF-8'?><modules><module name='presentation'>"
        absolute_url = get_domain_for_portal(CosinnusPortal.get_current()) + presentation_url
        xml += f"<document url='{absolute_url}' />"
        xml += "</module></modules>"
        response = requests.post(url, data=xml, headers=headers)
    else:
        response = requests.get(url)
    result = bbb_utils.parse_xml(response.content.decode('utf-8'))

    if result:
        return result
    else:
        logger.error('BBB Room error: Server request `start` was not successful.',
                     extra={'response_status_code': response.status_code, 'result': response.text})
        raise Exception('BBB Room exception: Server request was not successful: ' + str(response.text))


def end_meeting(meeting_id, password):
    """ This function is a wrapper for the `end_meeting` function in bbb.py """
    api_url = get_current_bbb_server_auth_pair_or_raise()[0]
    call = 'end'
    query = urllib.parse.urlencode((
        ('meetingID', meeting_id),
        ('password', password),
    ))
    hashed = api_call(query, call)
    url = api_url + call + '?' + hashed
    req = requests.get(url)
    result = bbb_utils.parse_xml(req.content)
    if result:
        return True
    else:
        return False


def get_meetings():
    """ This function is a wrapper for the `get_meetings` function in bbb.py

    :return: XML representation of the API result
    :rtype: XML
    """
    api_url = get_current_bbb_server_auth_pair_or_raise()[0]
    call = 'getMeetings'
    query = urllib.parse.urlencode((
        ('random', 'random'),
    ))
    hashed = api_call(query, call)
    url = api_url + call + '?' + hashed
    response = requests.get(url)
    result = bbb_utils.parse_xml(response.content)
    if result:
        # Create dict of values for easy use in template
        d = []
        r = result[1].findall('meeting')
        for m in r:
            meeting_id = m.find('meetingID').text
            password = m.find('moderatorPW').text
            d.append({
                'name': meeting_id,
                'running': m.find('running').text,
                'moderator_pw': password,
                'attendee_pw': m.find('attendeePW').text,
                'info': meeting_info(
                    meeting_id,
                    password)
            })
        return d
    else:
        logger.error('BBB Room error: Server request `getMeetings` was not successful.',
                     extra={'response_status_code': response.status_code, 'result': response.text})
        raise Exception("Get meetings() returned an error" + str(response.text))


def meeting_info(meeting_id, password):
    api_url = get_current_bbb_server_auth_pair_or_raise()[0]
    call = 'getMeetingInfo'
    query = urllib.parse.urlencode((
        ('meetingID', meeting_id),
        ('password', password),
    ))
    hashed = api_call(query, call)
    url = api_url + call + '?' + hashed
    response = bbb_utils.parse_xml(requests.get(url).content)
    if response:
        return bbb_utils.xml_to_json(response)
    else:
        return None


def is_running(meeting_id):
    """ This function is a wrapper for the `is_running` function in bbb.py

    :return: XML representation of the API result
    :rtype: XML
    """
    api_url = get_current_bbb_server_auth_pair_or_raise()[0]
    call = 'isMeetingRunning'
    query = urllib.parse.urlencode((
        ('meetingID', meeting_id),
    ))
    hashed = api_call(query, call)
    url = api_url + call + '?' + hashed
    result = bbb_utils.parse_xml(requests.get(url).content)
    if result and result.find('running').text == 'true':
        return True
    else:
        return False


def xml_join(name, meeting_id, password):
    """ Returns a XML representation of the join call. !! Use only in Testing !!

    :param name: Name of the user shown to other attendees in the conversation
    :type: str

    :param meeting_id: Identifier of the meeting
    :type: str

    :param password: Password for the user to join
    :type: str
    """
    
    api_url = get_current_bbb_server_auth_pair_or_raise()[0]
    call = 'join'
    query = urllib.parse.urlencode((
        ('fullName', name),
        ('meetingID', meeting_id),
        ('password', password),
        ('redirect', "false"),
    ))

    hashed = api_call(query, call)
    url = api_url + call + '?' + hashed
    result = bbb_utils.parse_xml(requests.get(url).content.decode('utf-8'))

    return result


def join_url(meeting_id, name, password, extra_parameter_dict=None):
    """ returns the join api url with parameters and hash to join a conversation1

    :param meeting_id: ID of the meeting to join
    :type: str

    :param name: Name of the user to join
    :type: str

    :param password:
    
    :param extra_parameter_dict: Any extra parameters for the user join link.
            See https://docs.bigbluebutton.org/2.2/customize.html#passing-custom-parameters-to-the-client-on-join
    :type dict


    :return: XML representation of the API result
    :rtype: XML
    """
    api_url = get_current_bbb_server_auth_pair_or_raise()[0]
    call = 'join'
    params_dict = {
        'fullName': name,
        'meetingID': meeting_id,
        'password': password,
    }
    if extra_parameter_dict:
        params_dict.update(extra_parameter_dict)
    query = urllib.parse.urlencode(params_dict)
    hashed = api_call(query, call)
    url = api_url + call + '?' + hashed
    return url
