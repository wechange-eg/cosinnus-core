# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from haystack import indexes

from cosinnus.utils.search import BaseTaggableObjectIndex, StoredDataIndexMixin,\
    CommaSeperatedIntegerMultiValueField, TimezoneAwareHaystackDateTimeField

from cosinnus_event.models import Event, EventAttendance,\
    annotate_attendants_count
from cosinnus.utils.functions import normalize_within_stddev
from django.utils.timezone import now


class EventIndex(BaseTaggableObjectIndex, StoredDataIndexMixin, indexes.Indexable):
    
    from_date = TimezoneAwareHaystackDateTimeField(model_attr='from_date', null=True)
    to_date = TimezoneAwareHaystackDateTimeField(model_attr='to_date', null=True)
    event_state = indexes.IntegerField(model_attr='state', null=True)
    participants = indexes.MultiValueField(stored=True, indexed=False)
    liked_user_ids = CommaSeperatedIntegerMultiValueField(indexed=False, stored=True)
    
    def get_model(self):
        return Event
    
    def get_image_field_for_background(self, obj):
        return obj.attached_image.file if obj.attached_image else None
    
    def prepare_description(self, obj):
        return obj.note
    
    def prepare_participant_count(self, obj):
        """ Attendees for events """
        return len(self.prepare_participants(obj)) #obj.attendances.filter(state__gt=EventAttendance.ATTENDANCE_NOT_GOING).count()
    
    def prepare_liked_user_ids(self, obj):
        return obj.get_liked_user_ids()
    
    def prepare_participants(self, obj):
        if not hasattr(obj, '_participants'):
            obj._participants = list(obj.attendances.filter(state__gt=EventAttendance.ATTENDANCE_NOT_GOING).values_list('user__id', flat=True))
        return obj._participants
    
    def boost_model(self, obj, indexed_data):
        """ We boost a combined measure of 2 added factors: soonishnes (50%) and participant count (50%).
            This means that a soon happening event with lots of participants will rank highest and an far off event 
            with no participants lowest.
            But it also means that soon happening events with no participants will still rank quite high, 
            as will far off events with lots of participants.
            
            Factors:
            - 50%: the event's participant count, normalized over the mean/stddev of the participant count of all 
                other events, in a range of [0.0..1.0]
            - 50%: the event's date, highest being now() and lowest >= 12 months from now
            """
        
        def qs_func():
            return annotate_attendants_count(Event.get_current_for_portal())
        
        mean, stddev = self.get_mean_and_stddev(qs_func, 'attendants_count', non_annotated_property=True)
        current_participant_count = self.prepare_participant_count(obj)
        rank_from_participants = normalize_within_stddev(current_participant_count, mean, stddev, stddev_factor=1.0)
        
        if obj.from_date:
            future_date_timedelta = obj.from_date - now()
            if future_date_timedelta.days < 0:
                rank_from_date = 0.0  # past events rank worst 
            else:
                rank_from_date = max(1.0 - (future_date_timedelta.days/365.0), 0) 
        else:
            rank_from_date = 0.0
            
        return (rank_from_participants / 2.0) + (rank_from_date / 2.0)
    
    def index_queryset(self, using=None):
        qs = super(EventIndex, self).index_queryset(using=using)
        # exclude hidden proxy from search index
        qs = qs.exclude(is_hidden_group_proxy=True).filter(conferenceevent__isnull=True)
        return qs
    
    def should_update(self, instance, **kwargs):
        should = super(EventIndex, self).should_update(instance, **kwargs)
        return should and not instance.is_hidden_group_proxy 
    
    