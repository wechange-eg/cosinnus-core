# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from fcm_django.models import FCMDevice
from firebase_admin import messaging

from cosinnus.conf import settings
from cosinnus.utils.user import is_user_active

logger = logging.getLogger('cosinnus')


def send_firebase_message(
    user,
):
    if not settings.COSINNUS_FIREBASE_ENABLED:
        return False  # TODO proper error return messages
    # never send
    if not user.is_authenticaed or not is_user_active(user):
        return False  # TODO proper error return messages

    empty_message = messaging.Message()
    user_devices = FCMDevice.objects.filter(user=user)
    # device_count = user_devices.count()
    responsedict = user_devices.send_message(empty_message)  # firebase_admin.messaging.FirebaseResponseDict

    multi_resp_str = ''
    for single_response in responsedict.response.responses:  # firebase_admin.messaging.SendResponse
        multi_resp_str += str(
            (
                'message_id',
                single_response.message_id,
                'success',
                single_response.success,
                'exception',
                single_response.exception,
                '<br/>',
            )
        )
