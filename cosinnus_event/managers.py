# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from datetime import timedelta
import pytz

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone

from taggit.models import TaggedItem
from django.contrib.auth.models import AnonymousUser


class EventQuerySet(models.QuerySet):
    
    def public(self):
        from cosinnus.utils.permissions import filter_tagged_object_queryset_for_user
        return filter_tagged_object_queryset_for_user(self, AnonymousUser())

    def all_upcoming(self):
        from cosinnus_event.models import upcoming_event_filter
        return upcoming_event_filter(self)

    def public_upcoming(self):
        from cosinnus_event.models import upcoming_event_filter
        return upcoming_event_filter(self.public())

    def conference_upcoming(self):
        """Filter upcoming events"""
        queryset = self.filter(to_date__gte=(timezone.now() - timedelta(minutes=10)))
        return self.filter(type__in=self.model.TIMELESS_TYPES) | queryset
    
    def archived(self):
        return self.filter(state=self.model.STATE_ARCHIVED_DOODLE)
    
    def tags(self):
        event_type = ContentType.objects.get(app_label="cosinnus_event", model="event")

        tag_names = []
        for ti in TaggedItem.objects.filter(content_type_id=event_type):
            if ti.tag.name not in tag_names:
                tag_names.append(ti.tag.name)

        return tag_names
