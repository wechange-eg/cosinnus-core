import logging
from threading import Thread

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db import transaction
from django.urls import reverse

from cosinnus_event.conf import settings
from cosinnus_event.utils.bbb_streaming import trigger_streamer_status_changes

logger = logging.getLogger('cosinnus')


class BBBRoomMixin(models.Model):
    """ 
    Mixin that provides the functionality of BBB video conferences into event models
    """
    class Meta(object):
        abstract = True
    
    conference_settings_assignments = GenericRelation('cosinnus.CosinnusConferenceSettings')

    def save(self, *args, **kwargs):        
        # call previous model
        super().save(*args, **kwargs)
        
        if self.can_have_bbb_room():
            # we do not create a bbb room on the server yet, that only happens
            # once  `get_bbb_room_url()` is called
            try:
                self.sync_bbb_members()
            except Exception as e:
                logger.exception(e)
                
        # save changed properties of the BBBRoom
        self.check_and_sync_bbb_room()

    def can_have_bbb_room(self):
        """ 
        Check if this event may have a BBB room.
        Returns 'False' since this is just a stub: add a funktion with the very same name into a model 
        you are going to use the mixin with. See the 'ConferenceEvent' model for details.
        """
        return False
    
    def get_bbb_room_nature(self):
        """ Stub to set the nature for a bbb-room depending on its type of source object.
            A nature for a bbb room is a property that determines differences in its 
            create/join API-call parameters that can be configured via
            `settings.BBB_PARAM_PORTAL_DEFAULTS or dynamically in the 
            `CosinnusConferenceSettings.bbb_params` json-field of each configuration object.
            These may be set by an admin or dynamically using presets fields. 
            
            This allows bbb rooms to behave differently depending on what type of conference event
            they are displayed in, like the instant-join nature of CoffeeTables
            
            A nature will be retrieved during CosinnusConferenceSettings agglomeration time,
            from the source object through this method, and set for the settings object itself.
            When the bbb params are retrieved for a BBB-API call like create/join using 
            `CosinnusConferenceSettings.get_finalized_bbb_params` the nature-specific call params
            for the set nature are merged over the base non-nature params of that settings object.
            
            Example: for a 'coffee' nature, the 'join__coffee' api-call param key in the JSON
                is merged over the 'join' api-call param key.
                
            @return: a nature string or None
        """
        return None
    
    def get_max_participants(self):
        """ Returns the number of participants allowed in the room
            @param return: a number between 0-999. """
        return settings.COSINNUS_CONFERENCE_COFFEETABLES_MAX_PARTICIPANTS_DEFAULT
    
    def get_presentation_url(self):
        """ Stub for the presentation URL used in create calls """ 
        return None
    
    def get_name_for_bbb_room(self):
        """ Overridable function to return the name of the BBB room differently
            depending on the source object """
        return self.get_readable_title()
    
    def get_meeting_id_for_bbb_room(self):
        """ Overridable function to return the meeting id of the BBB room differently
            depending on the source object """
        return f'{settings.COSINNUS_PORTAL_NAME}-{self.id}'
    
    def get_group_for_bbb_room(self):
        """ Overridable function to the group for this BBB room. Can be None. """
        return self.group
    
    def get_members_for_bbb_room(self):
        """ Overridable function to return a list of users that should be a member
            of this BBB room (as opposed to a moderator) """
        group = self.get_group_for_bbb_room()
        if group:
            return list(get_user_model().objects.filter(id__in=group.members).exclude(email__startswith='__deleted_user__'))
        return []
    
    def get_moderators_for_bbb_room(self):
        """ Overridable function to return a list of users that should be a moderator
            of this BBB room (with higher priviledges than a member) """
        group = self.get_group_for_bbb_room()
        if group:
            manager_ids = group.admins + group.managers
            return list(get_user_model().objects.filter(id__in=manager_ids).exclude(email__startswith='__deleted_user__'))
        return []
    
    def check_and_create_bbb_room(self, threaded=True):
        """ Can be safely called at any time to create a BBB room for this source object
            if it doesn't have one yet.
            @return True if a room needed to be created, False if none was created """
        # if source object is of the right type and has no BBB room yet,
        if self.can_have_bbb_room() and not self.media_tag.bbb_room:
            # be absolutely sure that no room has been created right now
            self.media_tag.refresh_from_db()
            if self.media_tag.bbb_room:
                return False
            
            # start a thread and create a BBB Room
            source_obj = self
            def create_room():
                from cosinnus.models.bbb_room import BBBRoom
                bbb_room = BBBRoom.create(
                    name=source_obj.get_name_for_bbb_room(), # todo name for item
                    meeting_id=source_obj.get_meeting_id_for_bbb_room(),
                    source_object=source_obj,
                    presentation_url=source_obj.get_presentation_url(),
                )
                source_obj.media_tag.bbb_room = bbb_room
                source_obj.media_tag.save()
                # sync all bb users
                source_obj.sync_bbb_members()

            if threaded:
                class CreateBBBRoomThread(Thread):
                    def run(self):
                        create_room()
                CreateBBBRoomThread().start()
            else:
                create_room()
            return True
        return False

    def check_and_sync_bbb_room(self):
        """ Will check if there is a BBBRoom attached to this event,
            and if so, sync the settings like participants from this event with it """
        if hasattr(self, 'media_tag') and self.media_tag.bbb_room:
            bbb_room = self.media_tag.bbb_room
            bbb_room.name = self.get_name_for_bbb_room()
            bbb_room.presentation_url = self.get_presentation_url()
            bbb_room.save()
    
    def sync_bbb_members(self):
        """ Completely re-syncs all users for this room """
        if self.media_tag.bbb_room:
            bbb_room = self.media_tag.bbb_room
            with transaction.atomic():
                bbb_room.remove_all_users()
                bbb_room.join_users(list(self.get_members_for_bbb_room()), as_moderator=False)
                bbb_room.join_users(list(self.get_moderators_for_bbb_room()), as_moderator=True)
                
    def get_admin_change_url(self):
        """ Stub that all inheriting objects should implement.
            Returns the django admin edit page for this object. """
        return None
    
    def get_bbb_room_url(self):
        if not self.can_have_bbb_room():
            return None
        if self.can_have_bbb_room() and not self.media_tag.bbb_room:
            self.check_and_create_bbb_room(threaded=True)
            # redirect to a temporary URL that refreshes
            return reverse('cosinnus:bbb-room-queue', kwargs={'mt_id': self.media_tag.id})
        return self.media_tag.bbb_room.get_absolute_url()
    
    def get_bbb_room_queue_api_url(self):
        if not self.can_have_bbb_room():
            return None
        if not settings.COSINNUS_TRIGGER_BBB_ROOM_CREATION_IN_QUEUE:
            # create a room here if mode is on hesitant-creation
            if self.can_have_bbb_room() and not self.media_tag.bbb_room:
                self.check_and_create_bbb_room(threaded=True)
            # redirect to a temporary URL that refreshes
        return reverse('cosinnus:bbb-room-queue-api', kwargs={'mt_id': self.media_tag.id})
    
    def get_parent_bbb_chain_object(self):
        """ Returns the parent of this object in the BBB conference settings hierarchy chain,
            or None """
        from cosinnus.models.conference import get_parent_object_in_conference_setting_chain
        return get_parent_object_in_conference_setting_chain(self)
    
    def get_conference_settings_object(self):
        """ Returns an inherited agglomeration of the conference settings attached to
            this object and all higher-up objects in the inheritance chain or None, 
            if arrived at the top.
            @return: None or a CosinnusConferenceSettings object """
        from cosinnus.models.conference import CosinnusConferenceSettings
        return CosinnusConferenceSettings.get_for_object(self)
    
    def get_parent_conference_settings_object(self):
        """ Like `get_conference_settings_object`, but returns an inherited agglomeration 
            of the conference settings attached to *the parent* of this object and all 
            higher-up objects in the inheritance chain or None, if arrived at the top.
            @return: None or a CosinnusConferenceSettings object """
        from cosinnus.models.conference import CosinnusConferenceSettings
        parent = self.get_parent_bbb_chain_object()
        if parent:
            return CosinnusConferenceSettings.get_for_object(parent)
        return None
    
    def get_finalized_bbb_params(self):
        """ Returns a dict of BBB params configured for this object,
            merged for the nature of the object, or the portal default params. """
        settings_object = self.get_conference_settings_object()
        if settings_object:
            return settings_object.get_finalized_bbb_params()
        return settings.BBB_PARAM_PORTAL_DEFAULTS
    
    def get_inherited_bbb_params_from_parent(self):
        """ Returns a dict of BBB params inherited by the parents for this object,
            or the portal default params. """
        settings_object = self.get_parent_conference_settings_object()
        if settings_object:
            return settings_object.get_raw_bbb_params()
        return settings.BBB_PARAM_PORTAL_DEFAULTS
    
