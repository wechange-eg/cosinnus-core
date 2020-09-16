from __future__ import unicode_literals

from builtins import object
import logging
from django.views.generic.base import RedirectView
from annoying.functions import get_object_or_None
from cosinnus.models.bbb_room import BBBRoom
from django.http.response import HttpResponseNotFound, HttpResponseNotAllowed
from cosinnus.core.decorators.views import redirect_to_not_logged_in,\
    redirect_to_403
from cosinnus.utils.permissions import check_user_superuser
from cosinnus.apis import bigbluebutton as bbb
import time

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
        
        room = get_object_or_None(BBBRoom, id=room_id)
        if room is None:
            return HttpResponseNotFound('Room does not exist.')
        if not user in room.attendees.all() and not user in room.moderators.all() \
                and not check_user_superuser(user):
            return redirect_to_403(self.request, view=self)
        
        self.room = room
        return super(BBBRoomMeetingView, self).get(*args, **kwargs)
    
    def get_redirect_url(self, *args, **kwargs):
        name = self.request.user.full_name

        if self.room:
            password = self.room.get_password_for_user(self.request.user) \
                if not check_user_superuser(self.request.user) else self.room.attendee_password

            if bbb.is_meeting_remote(self.room.meeting_id):
                return bbb.join_url_tokenized(self.room.meeting_id, name, password)
            else:
                self.room.restart()
                time.sleep(1)
                return bbb.join_url_tokenized(self.room.meeting_id, name, password)
        else:
            url = 'todo'
            return url
        
        
bbb_room_meeting = BBBRoomMeetingView.as_view()
