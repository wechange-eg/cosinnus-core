# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from typing import List, Tuple

from fcm_django.models import FCMDevice, FirebaseResponseDict
from firebase_admin import messaging
from firebase_admin.messaging import SendResponse

from cosinnus.conf import settings
from cosinnus.utils.user import is_user_active

logger = logging.getLogger('cosinnus')


def send_firebase_message(user) -> Tuple[List[SendResponse], List[SendResponse]]:
    """Send an empty firebase message to all devices of a user. This method
    does not worry about whether the messaged were sent successfully.
    @return: a tuple of (successful_responses, failed_responses)"""
    # TODO: raise exception here, and handle it in calling functions?
    if not settings.COSINNUS_FIREBASE_ENABLED:
        return [], []
    # never send Messages to inactive users
    if not user or not user.is_authenticated or not is_user_active(user):
        return [], []  # we're not logging anything here

    empty_message = messaging.Message()
    user_devices = FCMDevice.objects.filter(user=user)
    # device_count = user_devices.count()
    responsedict: FirebaseResponseDict = user_devices.send_message(empty_message)
    send_responses: List[SendResponse] = responsedict.response.responses

    successful_responses: List[SendResponse] = [resp for resp in send_responses if resp.success]
    failed_responses: List[SendResponse] = [resp for resp in send_responses if not resp.success]
    return successful_responses, failed_responses
