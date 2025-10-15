# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging
from typing import List, Tuple

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.dispatch import receiver
from fcm_django.models import FCMDevice, FirebaseResponseDict
from firebase_admin import messaging
from firebase_admin.messaging import SendResponse

from cosinnus.celery import app as celery_app
from cosinnus.conf import settings
from cosinnus.core import signals
from cosinnus.tasks import CeleryThreadTask
from cosinnus.utils.user import is_user_active

logger = logging.getLogger('cosinnus')

FIREBASE_USER_THROTTLE_CACHE_KEY = 'cosinnus/core/firebase/user_throttle/%(user_id)s'


def _send_firebase_message_direct(user, ignore_throttle=False) -> Tuple[List[SendResponse], List[SendResponse]]:
    """Directly send an empty firebase message to all devices of a single user if the account is active.
    This method does not worry about whether the messages were sent successfully.
    Does nothing if the user has no registered FCMDevice(s).
    @return: a tuple of (successful_responses, failed_responses)"""
    if not settings.COSINNUS_FIREBASE_ENABLED:
        return [], []
    # never send Messages to inactive users
    if not user or not user.is_authenticated or not is_user_active(user):
        return [], []  # we're not logging anything here
    # check throttle cache key to see if the user has just gotten an empty message and should not receive another yet
    user_throttle_cache_key = FIREBASE_USER_THROTTLE_CACHE_KEY % {'user_id': user.id}
    if settings.COSINNUS_FIREBASE_EMPTY_MESSAGE_USER_THROTTLE_SECONDS and not ignore_throttle:
        if cache.get(user_throttle_cache_key, False):
            if settings.DEBUG:
                print(f'DEBUG INFO: Not sending a firebase message as it was throttled for user id: {user.id}.')
            return [], []

    empty_message = messaging.Message()
    user_devices = FCMDevice.objects.filter(user=user)
    # device_count = user_devices.count()
    # does nothing if there are no devices for this user
    responsedict: FirebaseResponseDict = user_devices.send_message(empty_message)
    send_responses: List[SendResponse] = responsedict.response.responses

    # set throttle cache key
    if settings.COSINNUS_FIREBASE_EMPTY_MESSAGE_USER_THROTTLE_SECONDS:
        cache.set(user_throttle_cache_key, True, settings.COSINNUS_FIREBASE_EMPTY_MESSAGE_USER_THROTTLE_SECONDS)

    successful_responses: List[SendResponse] = [resp for resp in send_responses if resp.success]
    failed_responses: List[SendResponse] = [resp for resp in send_responses if not resp.success]
    if settings.DEBUG:
        debug_print = (
            'DEBUG INFO: Sent an empty firebase message to:\t\t'
            + 'user account '
            + str(user.email)
            + '\t\t'
            + 'successful responses were --> '
            + str([resp.message_id for resp in successful_responses])
            + '\t\tfailed responses were --> '
            + str([str((resp.message_id, str(resp.exception))) for resp in failed_responses])
        )
        print(debug_print)
    return successful_responses, failed_responses


@celery_app.task(base=CeleryThreadTask)
def _send_firebase_messages_task(user_ids):
    """For each user that was found by id, send an empty message to all of their registered devices."""
    users = get_user_model().objects.filter(id__in=user_ids, is_active=True)
    for user in users:
        # catch each exception because we never want the task to be retried by celery as a whole, as that
        # could mean duplicate messages being sent out
        try:
            _send_firebase_message_direct(user)
        except Exception as e:
            logger.warning(
                'An eror occurred while sending a Firebase message! Exception in extra.',
                extra={
                    'exception': e,
                    'user_id': user.id,
                },
            )


def send_firebase_message_threaded(user_ids: List[int]):
    """Send an empty Firebase message to users (in a Celery task / thread), to all of their registered devices."""
    if not settings.COSINNUS_FIREBASE_ENABLED or not user_ids:
        return
    _send_firebase_messages_task.delay(user_ids)


if settings.COSINNUS_FIREBASE_ENABLED:

    @receiver(signals.users_received_notification_alert)
    def users_received_notification_alert_hook(sender, user_ids, **kwargs):
        """A signal receiver that sends out empty firebase messages to each user that has just received
        a new `NotificationAlert`."""
        if user_ids:
            send_firebase_message_threaded(user_ids)
