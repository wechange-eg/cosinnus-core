# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from cosinnus.core import signals
from cosinnus.models.bbb_room import BBBRoom
from django.dispatch.dispatcher import receiver
from cosinnus_event.models import Event, ConferenceEvent
from threading import Thread
from cosinnus.models.group import MEMBER_STATUS, MEMBERSHIP_ADMIN
from django.db.models.signals import post_save
from annoying.functions import get_object_or_None
from cosinnus.models.group_extra import CosinnusConference
from django.contrib.contenttypes.models import ContentType
from cosinnus.models.tagged import BaseTaggableObjectReflection, BaseTagObject
import logging
from cosinnus.utils.functions import unique_aware_slugify

logger = logging.getLogger('cosinnus')


def update_bbb_room_memberships(group_membership, deleted):
    """ Apply membership permission changes to BBBRoom of all events and
        conference events in this group and the BBB room for the group itself. """
    group = group_membership.group
    events_in_group = Event.objects.filter(group=group).exclude(media_tag__bbb_room=None)
    bbb_room_source_objects = list(events_in_group) + [group]
    for source_obj in bbb_room_source_objects:
        if not source_obj.media_tag.bbb_room:
            continue
        room = source_obj.media_tag.bbb_room
        user = group_membership.user
        if deleted:
            room.remove_user(user)
        else:
            if group_membership.status in MEMBER_STATUS:
                as_moderator = bool(user in source_obj.get_moderators_for_bbb_room())
                room.join_user(user, as_moderator=as_moderator)


@receiver(signals.group_membership_has_changed)
def group_membership_has_changed_sub(sender, instance, deleted, **kwargs):
    """ Called after a CosinusGroupMembership is changed, to threaded apply membership permission
        changes to BBBRoom of all events in this group """
    
    class CreateBBBRoomUpdateThread(Thread):
        def run(self):
            update_bbb_room_memberships(instance, deleted)
    CreateBBBRoomUpdateThread().start()


@receiver(signals.group_saved_in_form)
def sync_hidden_conference_proxy_event(sender, group, user, **kwargs):
    """ For conferences that have a from_date and to_date set, create and keep in sync a single 
        event with `is_hidden_group_proxy=True`, that has the same name and datetime as the 
        conference itself. This event can be used in all normal views and querysets to display
        and handle the conference as proxy. Set related_groups in the conference to have
        the conference's proxy-event be displayed as one of those related_group's own event. """
    try:
        if group.pk and group.group_is_conference:
            proxy_event = get_object_or_None(Event, group=group, is_hidden_group_proxy=True)
            if proxy_event:
                if group.from_date is None or group.to_date is None:
                    proxy_event.delete()
                    return
            elif group.from_date is not None and group.to_date is not None:
                # only create proxy events for conferences with from_date and to_date set
                proxy_event = Event(
                    group=group,
                    is_hidden_group_proxy=True,
                    state=Event.STATE_SCHEDULED,
                    creator=user,
                )
            else:
                return
            
            # sync and save if proxy event and group differ in key attributes
            sync_attributes = [('name', 'title'), ('from_date', 'from_date'), ('to_date', 'to_date')]
            if any(getattr(proxy_event, attr[1]) != getattr(group, attr[0]) for attr in sync_attributes):
                for attr in sync_attributes:
                    setattr(proxy_event, attr[1], getattr(group, attr[0]))
                # set proxy event's slug to something unreachable so it never clashes with a real event
                if not proxy_event.slug:
                    unique_aware_slugify(proxy_event, 'title', 'slug', group=proxy_event.group)
                    proxy_event.slug = '__proxy__-' + proxy_event.slug
                proxy_event.save()
            
            # set proxy event to visible everywhere (since groups are visible anywhere as well)
            if not proxy_event.media_tag.visibility == BaseTagObject.VISIBILITY_ALL:
                proxy_event.media_tag.visibility = BaseTagObject.VISIBILITY_ALL
                proxy_event.media_tag.save()
            
            # for each related_group in the conference, reflect the proxy event into that group
            # and delete stale reflections
            ct = ContentType.objects.get_for_model(Event)
            prev_qs = BaseTaggableObjectReflection.objects.filter(content_type=ct, object_id=proxy_event.id)
            previous_reflections = dict((reflection.id, reflection) for reflection in prev_qs)
            for related_group in group.related_groups.all():
                attrs = {
                    'content_type': ct,
                    'object_id': proxy_event.id,
                    'group': related_group,
                }
                existing_reflection = get_object_or_None(BaseTaggableObjectReflection, **attrs)
                if existing_reflection:
                    # reflection exists and we can leave it. remove it from the dict
                    del previous_reflections[existing_reflection.id]
                else:
                    # create new reflection
                    attrs.update({
                        'creator': user,
                    })
                    BaseTaggableObjectReflection.objects.create(**attrs)
            # delete all stale reflections 
            # (the ones that exist but their groups are no longer tagged as related_group)
            for stale_reflection in previous_reflections.values():
                stale_reflection.delete()
        
    except Exception as e:
        logger.error('An error in cosinnus_event.hooks prevented saving the conference proxy events!',
                     extra={'exception': e})
            