from hashlib import sha1, sha256
import logging
import urllib

from django.core.exceptions import ImproperlyConfigured
import requests

from cosinnus.conf import settings
from cosinnus.models import CosinnusPortal, get_domain_for_portal
from cosinnus.utils import bigbluebutton as bbb_utils
from cosinnus.utils.functions import is_number, get_int_or_None
from cosinnus.models.conference import CosinnusConferenceSettings,\
    get_parent_object_in_conference_setting_chain
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.dates import datetime_from_timestamp

logger = logging.getLogger('cosinnus')


class BigBlueButtonAPI(object):
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
    
    api_auth_url = None
    api_auth_secret = None
    recording_api_auth_url = None
    recording_api_auth_secret = None
    
    class RecordingAPIServerNotSetUp(Exception):
        pass
    
    def __init__(self, source_object=None):
        """ Important: Which API target this object uses is determined
            by the source_object passed. On init we will check which CosinnusConferenceSetting
            in the inheritance hierarchy is set, and use the API settings of that.
            Check `CosinnusConferenceSettings.get_for_object()` for valid arguments
            :param source_object: The object the room is attached to. Can be a media_tag (BaseTagObject), ConferenceRoom,
                         ConferenceEvent, CosinnusGroup.
                         Default: current CosinnusPortal, if None is given. """
        self._set_current_bbb_server_auth(source_object=source_object)
        if not self.api_auth_url or not self.api_auth_secret:
            raise ImproperlyConfigured("No valid BBB server auth is currently configured or selected as active for this portal!")
        
    def _set_current_bbb_server_auth(self, source_object=None):
        """ Central helper function to retrieve and set the currently
            selected BBB-server API URL and Secret.
            
            Sets:
                - self.api_auth_url
                - self.api_auth_secret
                - self.recording_api_auth_url
                - self.recording_api_auth_secret
        """
                        
        current_portal = CosinnusPortal.get_current()
        if source_object is None:
            source_object = current_portal
        
        self.api_auth_url = None
        self.api_auth_secret = None
        self.recording_api_auth_url = None
        self.recording_api_auth_secret = None
        
        conference_settings = CosinnusConferenceSettings.get_for_object(source_object)
        if conference_settings:
            try:
                # find if the source object belongs to or is a group with premium status active
                if conference_settings.is_premium:
                    bbb_server_choice = conference_settings.bbb_server_choice_premium
                else:
                    bbb_server_choice = conference_settings.bbb_server_choice
                
                auth_pair = dict(settings.COSINNUS_BBB_SERVER_AUTH_AND_SECRET_PAIRS).get(bbb_server_choice)
                self.api_auth_url = auth_pair[0]
                self.api_auth_secret = auth_pair[1]
                
                recording_api_auth_pair = dict(settings.COSINNUS_BBB_SERVER_AUTH_AND_SECRET_PAIRS).get(conference_settings.bbb_server_choice_recording_api)
                if recording_api_auth_pair is not None:
                    self.recording_api_auth_url = recording_api_auth_pair[0]
                    self.recording_api_auth_secret = recording_api_auth_pair[1]
            except Exception as e:
                logger.error('Misconfigured: Either COSINNUS_BBB_SERVER_CHOICES or COSINNUS_BBB_SERVER_AUTH_AND_SECRET_PAIRS are not properly set up!',
                             extra={'exception': e})
                if settings.DEBUG:
                    raise
        
    def join_url_tokenized(self, meeting_id, name, password):
        url = self.join_url(meeting_id, name, password)
        return requests.get(url).url
    
    def api_call(self, query, call, secret=None):
        if secret is None:
            secret = self.api_auth_secret
        prepared = '{}{}{}'.format(call, query, secret)
    
        if settings.BBB_HASH_ALGORITHM == "SHA1":
            checksum = sha1(str(prepared).encode('utf-8')).hexdigest()
        elif settings.BBB_HASH_ALGORITHM == "SHA256":
            checksum = sha256(str(prepared).encode('utf-8')).hexdigest()
        else:
            raise ImproperlyConfigured("BBB_HASH_ALGORITHM setting is not set to SHA1 or SHA256")
    
        result = "%s&checksum=%s" % (query, checksum)
        return result
    
    
    def start(self, 
            name, meeting_id,
            moderator_password="", attendee_password="", voice_bridge=None,
            parent_meeting_id=None, options=None, presentation_url=""):
        """ This function calls the BigBlueButton API directly to create a meeting with all available parameters available
            in the cosinnus-core.BBBRoom model.
    
        :param name: Human readable name for the meeting
        :type: str
    
        :param meeting_id: Human readable ID for the meeting
        :type: str
    
        :param moderator_password: Password for users to join with moderator privileges
        :type: str
    
        :param attendee_password: Password for users to join with default attendee privileges
        :type: str
    
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
        
        call = 'create'
    
        # set default values
        voice_bridge = voice_bridge if voice_bridge and is_number(voice_bridge) else bbb_utils.random_voice_bridge()
        attendee_password = attendee_password if attendee_password else bbb_utils.random_password()
        moderator_password = moderator_password if moderator_password else bbb_utils.random_password()
        
        params = {}
        if options:
            params.update(options)
        # these are the options that aren't overwritable by JSON options
        params.update({
            "name": name,
            'meetingID': meeting_id,
            "voiceBridge": voice_bridge,
            "attendeePW": attendee_password,
            "moderatorPW": moderator_password,
        })
        if parent_meeting_id:
            params.update({
                "parentMeetingID": parent_meeting_id,
            })
        
        query = urllib.parse.urlencode(list(params.items()))
    
        hashed = self.api_call(query, call)
        url = self.api_auth_url + call + '?' + hashed
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
                         extra={'response_status_code': response.status_code, 'result': response.text,
                                'meeting_id': meeting_id, 'server_url': self.api_auth_url})
            raise Exception('BBB Room exception: Server request was not successful: ' + str(response.text))
    
    
    def end_meeting(self, meeting_id, password):
        """ This function is a wrapper for the `end_meeting` function in bbb.py """
        call = 'end'
        query = urllib.parse.urlencode((
            ('meetingID', meeting_id),
            ('password', password),
        ))
        hashed = self.api_call(query, call)
        url = self.api_auth_url + call + '?' + hashed
        req = requests.get(url)
        result = bbb_utils.parse_xml(req.content)
        if result:
            return True
        else:
            return False
    
    
    def get_meetings(self):
        """ This function is a wrapper for the `get_meetings` function in bbb.py
    
        :return: XML representation of the API result
        :rtype: XML
        """
        call = 'getMeetings'
        query = urllib.parse.urlencode((
            ('random', 'random'),
        ))
        hashed = self.api_call(query, call)
        url = self.api_auth_url + call + '?' + hashed
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
                    'info': self.meeting_info(
                        meeting_id,
                        password)
                })
            return d
        else:
            logger.error('BBB Room error: Server request `getMeetings` was not successful.',
                         extra={'response_status_code': response.status_code, 'result': response.text})
            raise Exception("Get meetings() returned an error" + str(response.text))
    
    
    def meeting_info(self, meeting_id, password):
        call = 'getMeetingInfo'
        query = urllib.parse.urlencode((
            ('meetingID', meeting_id),
            ('password', password),
        ))
        hashed = self.api_call(query, call)
        url = self.api_auth_url + call + '?' + hashed
        response = bbb_utils.parse_xml(requests.get(url).content)
        if response:
            return bbb_utils.xml_to_json(response)
        else:
            return None
    
    
    def is_running(self, meeting_id):
        """ This function is a wrapper for the `is_running` function in bbb.py
    
        :return: XML representation of the API result
        :rtype: XML
        """
        call = 'isMeetingRunning'
        query = urllib.parse.urlencode((
            ('meetingID', meeting_id),
        ))
        hashed = self.api_call(query, call)
        url = self.api_auth_url + call + '?' + hashed
        result = bbb_utils.parse_xml(requests.get(url).content)
        if result and result.find('running').text == 'true':
            return True
        else:
            return False
    
    
    def xml_join(self, name, meeting_id, password):
        """ Returns a XML representation of the join call. !! Use only in Testing !!
    
        :param name: Name of the user shown to other attendees in the conversation
        :type: str
    
        :param meeting_id: Identifier of the meeting
        :type: str
    
        :param password: Password for the user to join
        :type: str
        """
        
        call = 'join'
        query = urllib.parse.urlencode((
            ('fullName', name),
            ('meetingID', meeting_id),
            ('password', password),
            ('redirect', "false"),
        ))
    
        hashed = self.api_call(query, call)
        url = self.api_auth_url + call + '?' + hashed
        result = bbb_utils.parse_xml(requests.get(url).content.decode('utf-8'))
    
        return result
    
    
    def join_url(self, meeting_id, name, password, extra_parameter_dict=None):
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
        call = 'join'
        params_dict = {
            'fullName': name,
            'meetingID': meeting_id,
            'password': password,
        }
        if extra_parameter_dict:
            params_dict.update(extra_parameter_dict)
        query = urllib.parse.urlencode(params_dict)
        hashed = self.api_call(query, call)
        url = self.api_auth_url + call + '?' + hashed
        return url
    
    def get_recorded_meetings(self, group_id=None):
        """ This an implementation of the `getRecordings` API call for BBB.
            Will only retrieve recorded meetings with the meta tag assigning it to the current portal.
            Note: this uses a seperate API url and auth from the regular BBB servers!
            
            @param group_id: if supplied, will only return recorded meetings for the CosinnusGroup (conference)
                with the given id.
            :return: a list of JSON objects for the recorded meetings
        """
        
        if not self.recording_api_auth_secret or not self.recording_api_auth_url:
            raise self.RecordingAPIServerNotSetUp()
        
        call = 'getRecordings'
        portal_slug = CosinnusPortal.get_current().slug
        if group_id is not None:
            # NOTE: currently, ScaleLite can only OR query terms, not AND them, so we cannot filter for recordings
            # by querying for the meta tags for portal and group.
            # that's why we use this combined portal+group-id metatag "meta_we-portal-group-id" to filter with only one query
            query_params = [
                ('meta_we-portal-group-id', f'{portal_slug}-{group_id}'),
            ]
        else:
            query_params = [
                ('meta_we-portal', portal_slug),
            ]
        query = urllib.parse.urlencode(query_params)
        # Note: using different api urls for recording API calls
        hashed = self.api_call(query, call, secret=self.recording_api_auth_secret)
        url = self.recording_api_auth_url + call + '?' + hashed
        response = requests.get(url)
        
        if response.status_code == 200:
            # parse the recordings and extract data for each
            xml_content = bbb_utils.parse_xml(response.content)
            def _findtext(element, key):
                val = element.find(key)
                return val.text if val is not None else None
            try:
                recording_list = []
                # for a sample recording, see https://docs.bigbluebutton.org/dev/api.html#getrecordings
                for recording in xml_content.find('recordings'):
                    url = None
                    for format_entry in recording.find('playback').findall('format'):
                        if _findtext(format_entry, 'type') == 'presentation':
                            url = _findtext(format_entry, 'url')
                            break
                    # convert timestamps from milliseconds to seconds and to datetimes
                    start_time = get_int_or_None(_findtext(recording, 'startTime'))
                    if start_time:
                        start_time = datetime_from_timestamp(start_time // 1000)
                    end_time = get_int_or_None(_findtext(recording, 'endTime'))
                    if end_time:
                        end_time = datetime_from_timestamp(end_time // 1000)
                    json_recording = {
                        'id': _findtext(recording, 'recordID'),
                        'recordID': _findtext(recording, 'recordID'),
                        'meetingID': _findtext(recording, 'meetingID'),
                        'name': _findtext(recording, 'name'),
                        'url': url,
                        'participants': _findtext(recording, 'participants'),
                        'startTime': start_time,
                        'endTime': end_time,
                        'duration': end_time - start_time,
                    }
                    recording_list.append(json_recording)
                return recording_list
                
            except Exception as e:
                if settings.DEBUG:
                    raise
                logger.error('BBB Room error: Server request `getRecordings` response could not be parsed.',
                         extra={'response_status_code': response.status_code, 'result': response.text, 'exc': e})
                return None
        else:
            logger.error('BBB Room error: Server request `getRecordings` was not successful.',
                         extra={'response_status_code': response.status_code, 'result': response.text})
        return None
