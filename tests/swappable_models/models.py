# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import six

from django.db import models
from django.utils.encoding import force_text

from cosinnus.models.profile import BaseUserProfile


@six.python_2_unicode_compatible
class CustomUserProfile(BaseUserProfile):
    dob = models.DateField('Date of birth', null=True)

    def __str__(self):
        return "%s (%s)" % (force_text(self.user), force_text(self.dob))
