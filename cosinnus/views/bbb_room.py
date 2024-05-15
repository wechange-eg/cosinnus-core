from __future__ import unicode_literals

import logging
import time
from builtins import object

import requests
from annoying.functions import get_object_or_None
from django.contrib import messages
from django.http.response import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseNotFound,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect
from django.urls.base import reverse
from django.utils.translation import gettext as _
from django.views.generic.base import RedirectView, TemplateView, View

from cosinnus.conf import settings
from cosinnus.core.decorators.views import redirect_to_403, redirect_to_error_page, redirect_to_not_logged_in
from cosinnus.models.bbb_room import BBBRoom, BBBRoomVisitStatistics
from cosinnus.models.group import CosinnusPortal
from cosinnus.models.tagged import get_tag_object_model
from cosinnus.templatetags.cosinnus_tags import full_name
from cosinnus.utils.group import get_cosinnus_group_model
from cosinnus.utils.permissions import check_user_superuser
from cosinnus.utils.urls import group_aware_reverse
from cosinnus.views.mixins.group import RequireLoggedInMixin
from cosinnus_conference.forms import BBBGuestAccessForm
from cosinnus_conference.utils import BBBGuestTokenAnonymousUser

logger = logging.getLogger('cosinnus')


class BBBRoomMeetingView(RedirectView):
    """Generates a BBB-Room join URL for a logged in user depending on their permission level.
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
        if user not in room.attendees.all() and user not in room.moderators.all() and not check_user_superuser(user):
            return redirect_to_403(self.request, view=self)

        self.room = room
        return super(BBBRoomMeetingView, self).get(*args, **kwargs)

    def get_redirect_url(self, *args, **kwargs):
        """Checks whether a room is running and restarts it if not,
        then returns the rooms join URL for the current user"""
        return self.room.get_direct_room_url_for_user(self.request.user)


bbb_room_meeting = BBBRoomMeetingView.as_view()


class BBBRoomMeetingQueueView(RequireLoggedInMixin, RedirectView):
    """An intermediate view that can be visited for a BBB-Room that
    is in the process of being created, without blocking the code.
    The target object is the media_tag id. As long as the media_tag
    has no BBBRoom, it will show a waiting page, and if the tag has a
    room, it will redirect to the room URL"""

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
            return HttpResponse(
                '<html><head><meta http-equiv="refresh" content="5" ></head><body>Connnecting you to your room...</body></html>'
            )


bbb_room_meeting_queue = BBBRoomMeetingQueueView.as_view()


class BBBRoomMeetingQueueAPIView(View):
    """An intermediate view that can be visited for a BBB-Room that
    is in the process of being created, without blocking the code.
    The target object is the media_tag id. As long as the media_tag
    has no BBBRoom, it will show a waiting page, and if the tag has a
    room, it will redirect to the room URL.
    Very useful as a waiting-function to retrieve the final BBB room URL
    to insert into an iFrame (instead of relying on in-iframe redirects that
    break permission functionality in browsers).

    This view will require the session user to be logged in, or the following
    GET params to be provided and valid:
        - `guest_token`: str. a BBB guest_token matching the one from this
            media-tag's attached `BBBRoom` exactly
        - `username`: str. a non-empty username used for the BBB session
    """

    def get(self, *args, **kwargs):
        user = self.request.user
        guest_token = self.request.GET.get('guest_token', None)
        # allow anonymous access with a guest token
        if not user.is_authenticated and not guest_token:
            return HttpResponseBadRequest('Anonymous access is not permitted without a guest token.')

        media_tag_id = kwargs.get('mt_id')
        media_tag = get_object_or_404(get_tag_object_model(), id=media_tag_id)

        data = {
            'status': 'WAITING',
        }
        bbb_room = media_tag.bbb_room

        # return a waiting status or the concrete room URL on the BBB server wrapped in a result object
        if bbb_room is not None:
            if guest_token:
                if not bbb_room or not bbb_room.guest_token == guest_token:
                    # deny anonymous access to the bbb room if the token is not correct
                    return HttpResponseBadRequest('Invalid guest token.')

                if user.is_authenticated:
                    # set the temporary BBB user guest token for this join process
                    setattr(user, BBBRoom.BBB_USER_GUEST_TOKEN_ATTR, guest_token)
                else:
                    # set the temporary BBB user with name and guest token for this join process
                    username = self.request.GET.get('username', '').strip()
                    if not username:
                        return HttpResponseBadRequest('Username missing.')
                    user = BBBGuestTokenAnonymousUser()
                    setattr(user, BBBRoom.BBB_USER_GUEST_TOKEN_ATTR, guest_token)
                    setattr(user, 'bbb_user_name', username)
            elif (
                user not in bbb_room.attendees.all()
                and user not in bbb_room.moderators.all()
                and not check_user_superuser(user)
            ):
                # deny logged in users without a guest token if they have no permission to enter the room
                return HttpResponseBadRequest('User is not allowed to enter this room.')

            room_url = bbb_room.get_direct_room_url_for_user(user=user)
            if not room_url:
                return HttpResponseBadRequest('Room membership for this user could not be established.')
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
                    # this can happen when a room is still being created on the BBB server and
                    # we quickly ask BBBAtScale for its URL; it will return a "Room is still being created" error
                    logger.warn(
                        'BBB Queue Scale-Cluster URL resolve step did not receive a 200/302 response, retrying.',
                        extra={'response': response, 'response_text': response.text},
                    )
                    return JsonResponse(data)
            data = {
                'status': 'DONE',
                'url': room_url,
                'recorded_meeting': bbb_room.is_recorded_meeting,
            }
        elif bbb_room is None and settings.COSINNUS_TRIGGER_BBB_ROOM_CREATION_IN_QUEUE:
            # if the media_tag is attached to a conference event, but no room has been created yet,
            # create one
            from cosinnus_event.models import ConferenceEvent, Event  # noqa

            parent_event = get_object_or_None(ConferenceEvent, media_tag__id=media_tag_id)
            if not parent_event:
                parent_event = get_object_or_None(Event, media_tag__id=media_tag_id)
            if not parent_event:
                parent_event = get_object_or_None(get_cosinnus_group_model(), media_tag__id=media_tag_id)

            if parent_event and parent_event.can_have_bbb_room() and not parent_event.media_tag.bbb_room:
                parent_event.check_and_create_bbb_room(threaded=True)
        return JsonResponse(data)


bbb_room_meeting_queue_api = BBBRoomMeetingQueueAPIView.as_view()


class BBBRoomGuestAccessView(TemplateView):
    """Guest access for a specific BBB room where kwarg `guest_token` corresponds to
    a `BBBRoom.guest_token`.
    Will redirect to the direct BBB join URL if the user is logged in, or all GET
    params are filled. Will show a form where the user can enter their details,
    which redirects to this same view with filled GET params."""

    msg_invalid_token = _('Invalid guest token.')
    msg_error_redirecting = _(
        'There was an error when trying to redirect you to the BBB room. Please contact an administrator!'
    )
    template_name = 'cosinnus/conference/conference_bbb_guest_token_page.html'

    guest_token = None
    bbb_room = None
    source_obj = None
    source_group = None

    # data that has to be filled out if the user isn't authenticated
    username = None
    all_data_filled = False

    def get_source_group(self, source_obj):
        """Returns the parent group of the bbb-room's source object,
        whether it is a group itself or the conference of the conference event
        or the group of the Event with a bbb room.
        Returns None if none apply"""
        if source_obj:
            # try Group
            if type(source_obj) is get_cosinnus_group_model() or issubclass(
                source_obj.__class__, get_cosinnus_group_model()
            ):
                return source_obj
            elif getattr(source_obj, 'group', None):
                return source_obj.group
        return None

    def resolve_bbb_room_url_and_redirect(self, user):
        """For the given user, directly resolve the BBB room url and return it."""

        resolved_room_url = None
        direct_room_url = self.bbb_room.get_direct_room_url_for_user(user)

        class BBBErrorException(Exception):
            pass

        def _resolve_url(_room_url, retry=True):
            response = requests.get(_room_url, allow_redirects=False)
            if response.status_code == 302 and 'Location' in response.headers:
                return response.headers['Location']
            elif not response.status_code == 200:
                # this can happen when a room is still being created on the BBB server and
                # we quickly ask BBBAtScale for its URL; it will return a "Room is still being created" error
                if retry:
                    time.sleep(3)
                    return _resolve_url(_room_url, retry=False)
            elif response.status_code == 200:
                logger.error(
                    'BBB guest URL resolver: resolving URL response unexpected, cannot rediredt the user to their room!',
                    extra={
                        'response': response,
                        'response_text': response.text,
                        'guest_token': self.guest_token,
                        'user': user,
                        'room_id': self.bbb_room.id,
                    },
                )
                messages.error(self.request, self.msg_error_redirecting)
                raise BBBErrorException()

        try:
            resolved_room_url = _resolve_url(direct_room_url)
        except BBBErrorException:
            return redirect_to_error_page(self.request, view=self)

        if not resolved_room_url:
            return HttpResponse(
                '<html><head><meta http-equiv="refresh" content="5" ></head><body>Connnecting you to your room...</body></html>'
            )
        return HttpResponseRedirect(resolved_room_url)

    def get(self, request, *args, **kwargs):
        self.guest_token = kwargs.pop('guest_token', '').strip()
        # check if guest token exists
        if not self.guest_token:
            messages.warning(request, self.msg_invalid_token)
            return redirect_to_error_page(request, view=self)
        current_portal = CosinnusPortal.get_current()
        # match correct bbb room
        self.bbb_room = get_object_or_None(BBBRoom, portal=current_portal, guest_token=self.guest_token)
        if not self.bbb_room:
            messages.warning(request, self.msg_invalid_token)
            return redirect_to_error_page(request, view=self)

        user = self.request.user
        self.source_obj = self.bbb_room.source_object
        self.source_group = self.get_source_group(self.source_obj)
        if user.is_authenticated:
            # check if user is member of the bbb-room's source object and if so, redirect them to the room directly
            if self.source_group and self.source_group.is_member(user) and hasattr(self.source_obj, 'get_absolute_url'):
                if self.source_group == self.source_obj:
                    return redirect(group_aware_reverse('cosinnus:group-meeting', kwargs={'group': self.source_group}))
                return redirect(self.source_obj.get_absolute_url())

            # set the temporary BBB user guest token for this join process
            setattr(user, BBBRoom.BBB_USER_GUEST_TOKEN_ATTR, self.guest_token)
            self.all_data_filled = True
        else:
            # if the anonymous user didn't fill out all the data required, show the enter-username form
            self.username = request.GET.get('username', '').strip()
            tos_check = request.GET.get('tos_check', False) == 'true'
            if not self.username or not tos_check:
                return super().get(request, *args, **kwargs)
            # save username to session to autocomplete the username field next time for this user
            self.request.session['bbb_guest_username'] = self.username
            self.all_data_filled = True

            # set the temporary BBB user with name and guest token for this join process
            user = BBBGuestTokenAnonymousUser()
            setattr(user, BBBRoom.BBB_USER_GUEST_TOKEN_ATTR, self.guest_token)
            setattr(user, 'bbb_user_name', self.username)

        self.media_tag = self.source_obj and getattr(self.source_obj, 'media_tag', None) or None
        # without a media tag we cannot use the BBB queue API, so resolve the url and redirect directly
        if not self.media_tag:
            return self.resolve_bbb_room_url_and_redirect(user)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                'recording_prompt_required': self.bbb_room and self.bbb_room.is_recorded_meeting or False,
                'has_bbb_video': True,
                'meeting_name': self.bbb_room.name,
                'all_data_filled': self.all_data_filled,
                'source_group': self.source_group or None,
            }
        )
        if self.all_data_filled:
            meeting_url = reverse('cosinnus:bbb-room-queue-api', kwargs={'mt_id': self.media_tag.id})
            meeting_url = f'{meeting_url}?guest_token={self.guest_token}'
            if self.username:
                meeting_url += f'&username={self.username}'
            context.update(
                {
                    'meeting_url': meeting_url,
                }
            )
        else:
            context.update(
                {
                    'form': BBBGuestAccessForm(),
                }
            )
        return context


bbb_room_guest_access = BBBRoomGuestAccessView.as_view()
