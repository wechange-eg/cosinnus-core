# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from taggit.models import TaggedItem
from django.db import models


class EtherpadManager(models.Manager):

    def tags(self):
        event_type = ContentType.objects.get(app_label="cosinnus_etherpad", model="etherpad")

        tag_names = []
        for ti in TaggedItem.objects.filter(content_type_id=event_type):
            if ti.tag.name not in tag_names:
                tag_names.append(ti.tag.name)

        return tag_names
