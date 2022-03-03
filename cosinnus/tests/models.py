# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from cosinnus.models.tagged import BaseTaggableObjectModel


class SlugTestModel(BaseTaggableObjectModel):
    pass


class ChoicesTestModel(BaseTaggableObjectModel):
    STATE_SCHEDULED = 0
    STATE_VOTING_OPEN = 1
    STATE_CANCELED = 2

    STATE_CHOICES = (
        (STATE_SCHEDULED, 'Scheduled'),
        (STATE_VOTING_OPEN, 'Voting open'),
        (STATE_CANCELED, 'Canceled'),
    )

    state = models.PositiveIntegerField(
        'State',
        choices=STATE_CHOICES,
        default=STATE_VOTING_OPEN,
        editable=False,
    )
