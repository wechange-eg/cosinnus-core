from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse

from cosinnus.models import BBBRoom


def bbb_meetings(request, group_id):
    rooms = BBBRoom.objects.filter(conference__group__id=group_id)
    return list(rooms)


def join_meeting(request, meeting_id):
    if request.user:
        try:
            room = BBBRoom.objects.get(meeting_id=meeting_id)
            redirect_url = room.get_join_url(request.user)
            return redirect_url
        except ObjectDoesNotExist:
            return HttpResponse('Room not found')
    else:
        return HttpResponse('Insufficient user rights.')
