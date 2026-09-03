# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import timedelta

from django.contrib.auth.models import AnonymousUser
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from taggit.models import TaggedItem

from cosinnus.models import BaseTaggableObjectManager


class EventManager(BaseTaggableObjectManager):
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
        event_type = ContentType.objects.get(app_label='cosinnus_event', model='event')

        tag_names = []
        for ti in TaggedItem.objects.filter(content_type_id=event_type):
            if ti.tag.name not in tag_names:
                tag_names.append(ti.tag.name)

        return tag_names

    def get_personal_open_polls(self, user):
        """Return open user polls where the has not voted yet."""
        queryset = super().get_personal_items(user)
        # exclude groups with deactivated app
        queryset = queryset.exclude(group__deactivated_apps__contains='cosinnus_event')
        # consider only open polls
        queryset = queryset.filter(state=self.model.STATE_VOTING_OPEN)
        # consider only polls where the user has not voted yet
        queryset = queryset.exclude(suggestions__votes__voter__id=user.id)
        return queryset

    def get_personal_attending_events(self, user):
        """Return scheduled events where the user is attending."""
        from cosinnus_event.models import EventAttendance

        queryset = self.all_upcoming()
        queryset = queryset.filter(group__is_active=True)
        queryset = queryset.exclude(group__deactivated_apps__contains='cosinnus_event')
        queryset = queryset.filter(state=self.model.STATE_SCHEDULED)
        queryset = queryset.filter(attendances__state=EventAttendance.ATTENDANCE_GOING, attendances__user__id=user.id)
        return queryset

    def get_recommendations(self, user):
        queryset = super().get_recommendations(user)
        queryset = queryset.exclude(group__deactivated_apps__contains='cosinnus_event')
        queryset = queryset.filter(state=self.model.STATE_SCHEDULED)
        queryset = queryset.filter(from_date__gte=timezone.now())
        queryset = queryset.exclude(note=None)
        queryset = queryset.exclude(attendances__user__id=user.id)
        queryset = queryset.order_by('from_date')
        return queryset
