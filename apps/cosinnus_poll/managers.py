# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.contenttypes.models import ContentType
from django.db import models

from taggit.models import TaggedItem


class PollManager(models.Manager):
    def public(self):
        # Django 1.5: get_query_set, 1.7: get_queryset
        qs = getattr(self, 'get_queryset', self.get_query_set)()
        return qs.filter(public=True, state=self.model.STATE_SCHEDULED)

    def tags(self):
        poll_type = ContentType.objects.get(app_label="cosinnus_poll", model="poll")

        tag_names = []
        for ti in TaggedItem.objects.filter(content_type_id=poll_type):
            if ti.tag.name not in tag_names:
                tag_names.append(ti.tag.name)

        return tag_names
