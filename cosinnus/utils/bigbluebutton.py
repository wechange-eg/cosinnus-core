import random
import string

import xml.etree.ElementTree as ET


def xml_to_json(xml_data):
    """ converts a xml representation of a response to json"""
    result = {}
    if xml_data:
        for x in xml_data:
            result[x.tag] = x.text if x.text != '\n' else {}
    return result


def parse_xml(response):
    try:
        xml = ET.XML(response)
        code = xml.find('returncode').text
        if code == 'SUCCESS':
            return xml
        else:
            # TODO add logging statement
            message_key = xml.find('messageKey').text
            message = xml.find('message').text
            raise Exception("[{code}]: {key} - {message}".format(
                code=code, key=message_key, message=message
            ))
    except:
        return None


def random_meeting_id():
    """ generates a random meeting_id to identify the meeting at BigBlueButton """
    return "room-" + random_password()


def random_password(length=5):
    """ generates a random moderator password for a BBBRoom  with lowercase ASCII characters """
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))


def random_voice_bridge():
    """ generates a random voice bridge dial in PIN between 10000 and 99999 that is unique within all BBB-Rooms

    :return: random integer in the range of 10000 - 99999
    :rtype: int
    """
    # existing_pins = list(BBBRoom.objects.filter(ended=False).values_list("dial_number", flat=True))
    #
    # random_pin = 10000
    #
    # while True:
    #     random_pin = random.randint(10000, 99999)
    #     if random_pin not in existing_pins:
    #         break

    return random.randint(10000, 99999)
