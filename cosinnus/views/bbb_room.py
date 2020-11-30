from __future__ import unicode_literals

from builtins import object
import logging
import time

from annoying.functions import get_object_or_None
from django.http.response import HttpResponseNotFound, HttpResponseNotAllowed, \
    HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic.base import RedirectView

from cosinnus.apis import bigbluebutton as bbb
from cosinnus.conf import settings
from cosinnus.core.decorators.views import redirect_to_not_logged_in, \
    redirect_to_403
from cosinnus.models.bbb_room import BBBRoom, BBBRoomVisitStatistics
from cosinnus.models.tagged import get_tag_object_model
from cosinnus.templatetags.cosinnus_tags import full_name
from cosinnus.utils.permissions import check_user_superuser
from cosinnus.views.mixins.group import RequireLoggedInMixin


logger = logging.getLogger('cosinnus')


class BBBRoomMeetingView(RedirectView):
    """ Generates a BBB-Room join URL for a logged in user depending on their permission level. 
        Also makes sure the room is created on the BBB server.

        if a user is a superuser,but neither attendee or moderator, they join as attendee!
    """
    
    def get(self, *args, **kwargs):
        room_id = kwargs.get('room_id')
        user = self.request.user
        if not user.is_authenticated:
            return redirect_to_not_logged_in(self.request, view=self)
        
        room = get_object_or_None(BBBRoom, id=int(room_id))
        if room is None:
            return HttpResponseNotFound('Room does not exist.')
        if not user in room.attendees.all() and not user in room.moderators.all() \
                and not check_user_superuser(user):
            return redirect_to_403(self.request, view=self)
        
        self.room = room
        return super(BBBRoomMeetingView, self).get(*args, **kwargs)
    
    def get_redirect_url(self, *args, **kwargs):
        """ Checks whether a room is running and restarts it if not,
            then returns the rooms join URL for the current user """
        
        if not self.room.check_user_can_enter_room(self.request.user):
            return redirect_to_403(self.request, view=self)

        if not self.room.is_running:
            try:
                self.room.restart()
            except Exception as e:
                logger.exception(e)
        
        # add statistics visit
        try:
            room_event = self.room.event
            event_group = room_event and room_event.group or None
            BBBRoomVisitStatistics.create_user_visit_for_bbb_room(self.request.user, self.room, group=event_group)
        except Exception as e:
            if settings.DEBUG:
                raise
            logger.error('Error creating a statistic BBBRoom visit entry.', extra={'exception': e})
        
        return self.room.get_join_url(self.request.user)

bbb_room_meeting = BBBRoomMeetingView.as_view()


class BBBRoomMeetingQueueView(RequireLoggedInMixin, RedirectView):
    """ An intermediate view that can be visited for a BBB-Room that 
        is in the process of being created, without blocking the code.
        The target object is the media_tag id. As long as the media_tag
        has no BBBRoom, it will show a waiting page, and if the tag has a
        room, it will redirect to the room URL """
        
    def get(self, *args, **kwargs):
        media_tag_id = kwargs.get('mt_id')
        user = self.request.user
        if not user.is_authenticated:
            return redirect_to_not_logged_in(self.request, view=self)
        media_tag = get_object_or_404(get_tag_object_model(), id=media_tag_id)
        # show waiting message (with reload) or redirect to room if it exists now
        if media_tag.bbb_room is not None:
            return redirect(media_tag.bbb_room.get_absolute_url())
        else:
            return HttpResponse('<html><head><meta http-equiv="refresh" content="5" ></head><body>Connnecting you to your room...</body></html>')
    
bbb_room_meeting_queue = BBBRoomMeetingQueueView.as_view()
