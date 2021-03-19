from __future__ import unicode_literals

from builtins import object
import logging
import time

from annoying.functions import get_object_or_None
from django.http.response import HttpResponseNotFound, \
    HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.generic.base import RedirectView, View

from cosinnus.conf import settings
from cosinnus.core.decorators.views import redirect_to_not_logged_in, \
    redirect_to_403
from cosinnus.models.bbb_room import BBBRoom, BBBRoomVisitStatistics
from cosinnus.models.tagged import get_tag_object_model
from cosinnus.templatetags.cosinnus_tags import full_name
from cosinnus.utils.permissions import check_user_superuser
from cosinnus.views.mixins.group import RequireLoggedInMixin
import requests


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
        return self.room.get_direct_room_url_for_user(self.request.user)
        

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


class BBBRoomMeetingQueueAPIView(RequireLoggedInMixin, View):
    """ An intermediate view that can be visited for a BBB-Room that 
        is in the process of being created, without blocking the code.
        The target object is the media_tag id. As long as the media_tag
        has no BBBRoom, it will show a waiting page, and if the tag has a
        room, it will redirect to the room URL.
        Very useful as a waiting-function to retrieve the final BBB room URL
        to insert into an iFrame (instead of relying on in-iframe redirects that
        break permission functionality in browsers). """
        
    def get(self, *args, **kwargs):
        media_tag_id = kwargs.get('mt_id')
        user = self.request.user
        if not user.is_authenticated:
            return redirect_to_not_logged_in(self.request, view=self)
        media_tag = get_object_or_404(get_tag_object_model(), id=media_tag_id)
        
        data = {
            'status': "WAITING",
        }
        # return a waiting status or the concrete room URL on the BBB server wrapped in a result object
        if media_tag.bbb_room is not None:
            room_url = media_tag.bbb_room.get_direct_room_url_for_user(user=user)
            
            # if the URL matches a cluster URL, we check if the room_url returns a http redirect
            # and if so, return the redirect target.
            # this way, we peel the cluster gateway from the URL to be able to insert
            # the real server's URL into the iframe
            url_match_func = settings.COSINNUS_BBB_RESOLVE_CLUSTER_REDIRECTS_IF_URL_MATCHES
            if url_match_func and url_match_func(room_url):
                response = requests.get(room_url, allow_redirects=False)
                if response.status_code == 302 and 'Location' in response.headers:
                    room_url = response.headers['Location']
                elif not response.status_code == 200:
                    logger.error('BBB Queue final step did not receive a 200/302 response!', extra={'response': response.json()})
            data = {
                'status': "DONE", 
                'url': room_url,
            }
        elif media_tag.bbb_room is None and settings.COSINNUS_TRIGGER_BBB_ROOM_CREATION_IN_QUEUE:
            # if the media_tag is attached to a conference event, but no room has been created yet,
            # create one
            from cosinnus_event.models import ConferenceEvent #noqa
            conference_event = get_object_or_None(ConferenceEvent, media_tag__id=media_tag_id)
            if conference_event and conference_event.can_have_bbb_room() and not conference_event.media_tag.bbb_room:
                conference_event.check_and_create_bbb_room(threaded=True)
            
        return JsonResponse(data)
    
bbb_room_meeting_queue_api = BBBRoomMeetingQueueAPIView.as_view()
