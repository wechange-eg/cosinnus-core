# -*- coding: utf-8 -*-
import celery
from django.contrib.auth import get_user_model

from cosinnus.celery import app as celery_app
from cosinnus.models.group import CosinnusGroup
from cosinnus_message.rocket_chat import RocketChatConnection, RocketChatDownException


class RocketChatTask(celery.Task):
    # See: https://docs.celeryq.dev/en/stable/userguide/tasks.html#retrying
    # autoretry on following errors:
    autoretry_for = (RocketChatDownException,)
    # max number of retries
    max_retries = 10
    # exponential backoff starting with 10s (then 20s, 40s, ...)
    retry_backoff = 10
    # If enabled the retry delay is random between 0 and the delay computed by the backoff.
    retry_jitter = False
    # max retry delay
    retry_backoff_max = 600


@celery_app.task(base=RocketChatTask)
def rocket_group_membership_invite(user_pk, group_pk):
    user = get_user_model().objects.get(pk=user_pk)
    group = CosinnusGroup.objects.get(pk=group_pk)
    rocket = RocketChatConnection()
    rocket.groups_invite(user, group)

